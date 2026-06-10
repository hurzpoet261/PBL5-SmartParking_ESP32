# %% [markdown]
# # Train YOLO License Plate Detector for PBL5 Smart Parking on Kaggle
#
# Run this file in a Kaggle Notebook with GPU enabled:
# Notebook Settings -> Accelerator -> GPU T4 x2 or P100.
# Internet must be enabled for `pip install ultralytics`.
#
# Expected dataset format after unzip:
#
# ```text
# dataset/
#   data.yaml                  # optional; script can create it
#   images/
#     train/*.jpg
#     val/*.jpg
#     test/*.jpg               # optional
#   labels/
#     train/*.txt
#     val/*.txt
#     test/*.txt               # optional
# ```
#
# Label format is YOLO detection:
#
# ```text
# class_id x_center y_center width height
# ```
#
# For this project use one class only:
# class id `0` = `license_plate`
#
# Label the full license plate rectangle, not just OCR characters.

# %%
from __future__ import annotations

import os
import random
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile


# =============================================================================
# CONFIG
# =============================================================================

# Kaggle mounts datasets under /kaggle/input/<dataset-slug>.
# Set this to either:
# - an extracted YOLO dataset folder
# - a folder that contains the YOLO dataset folder
# - a .zip file containing the YOLO dataset
#
# Example after adding a Kaggle dataset named "license-plate-yolo-dataset":
# /kaggle/input/license-plate-yolo-dataset
DATASET_SOURCE = Path("/kaggle/input/license-plate-yolo-dataset")

# Working directory inside Kaggle. Files here can be downloaded from Output.
WORK_DIR = Path("/kaggle/working/pbl5_plate_training")
DATASET_DIR = WORK_DIR / "dataset"
RUNS_DIR = WORK_DIR / "runs"

# Model choice:
# - yolov8n.pt: fastest, lower accuracy
# - yolov8s.pt: good after labels are verified
# - yolov8m.pt: stronger, slower
BASE_MODEL = "yolov8n.pt"

EPOCHS = 40
IMGSZ = 640
BATCH = 8
PATIENCE = 10
SEED = 42
USE_DDP = True
DEVICE = "0,1" if USE_DDP else 0
WORKERS = 1

# Runtime confidence to preview predictions after training.
PREDICT_CONF = 0.20

# Output checkpoint copied here. Download it from Kaggle Notebook Output.
OUTPUT_DIR = Path("/kaggle/working/yolo_plate_runs")

# Optional: if you upload/clone this repo inside Kaggle, set this to a real path.
REPO_MODEL_OUTPUT = Path("/kaggle/working/PBL5-SmartParking_ESP32/backend_v3/models/license_plate_detector.pt")

CLASS_NAMES = ["license_plate"]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# Keep this False on Kaggle. Many exported datasets contain data.yaml with a
# Windows path such as D:/..., which breaks after copying to /kaggle/working.
PRESERVE_EXISTING_DATA_YAML = False

# Kaggle needs Internet enabled to install packages from PyPI. If your notebook
# already has ultralytics installed or you attach an offline wheel, set this to
# False.
INSTALL_ULTRALYTICS = True
ULTRALYTICS_VERSION = "8.3.40"

# Keep this True while auditing labels. If preview boxes are correct, change it
# to False and rerun the notebook to train.
STOP_AFTER_LABEL_PREVIEW = True

# What to do with invalid YOLO label files in the extracted Kaggle copy.
# - "fail": stop and print a report.
# - "skip_bad_samples": move bad image/label files out of images/* and labels/*.
INVALID_LABEL_POLICY = "skip_bad_samples"
INVALID_SAMPLE_DIR = WORK_DIR / "_invalid_samples"

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")


# =============================================================================
# SETUP
# =============================================================================

def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.check_call(command)


def install_dependencies() -> None:
    if not INSTALL_ULTRALYTICS:
        print("[SETUP] INSTALL_ULTRALYTICS=False, skipping pip install")
        return

    try:
        import ultralytics  # noqa: F401

        print("[SETUP] ultralytics already installed")
        return
    except ImportError:
        pass

    try:
        run([
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "--no-deps",
            f"ultralytics=={ULTRALYTICS_VERSION}",
        ])
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "Failed to install ultralytics. In Kaggle, enable Internet in "
            "Notebook Settings, or set INSTALL_ULTRALYTICS=False if the package "
            "is already available/offline-installed."
        ) from exc


def reset_work_dir() -> None:
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def copy_dataset_source() -> None:
    if not DATASET_SOURCE.exists():
        raise FileNotFoundError(
            f"Dataset source not found: {DATASET_SOURCE}\n"
            "Add your YOLO dataset to the Kaggle Notebook and update DATASET_SOURCE."
        )

    if DATASET_SOURCE.is_file() and DATASET_SOURCE.suffix.lower() == ".zip":
        print(f"[DATASET] Extracting {DATASET_SOURCE} -> {DATASET_DIR}")
        with ZipFile(DATASET_SOURCE) as archive:
            archive.extractall(DATASET_DIR)
        return

    if DATASET_SOURCE.is_file():
        raise ValueError(f"Unsupported dataset file type: {DATASET_SOURCE}")

    zip_files = sorted(DATASET_SOURCE.glob("*.zip"))
    has_yolo_dirs = (
        (DATASET_SOURCE / "images" / "train").exists()
        or any((path / "images" / "train").exists() for path in DATASET_SOURCE.rglob("*") if path.is_dir())
    )
    if zip_files and not has_yolo_dirs:
        zip_path = zip_files[0]
        print(f"[DATASET] Found zip inside source: {zip_path}")
        print(f"[DATASET] Extracting {zip_path} -> {DATASET_DIR}")
        with ZipFile(zip_path) as archive:
            archive.extractall(DATASET_DIR)
        return

    target = DATASET_DIR / DATASET_SOURCE.name
    print(f"[DATASET] Copying {DATASET_SOURCE} -> {target}")
    shutil.copytree(DATASET_SOURCE, target, dirs_exist_ok=True)


# =============================================================================
# DATASET DISCOVERY AND VALIDATION
# =============================================================================

def find_dataset_root(base: Path) -> Path:
    candidates = []
    for path in [base, *base.rglob("*")]:
        if not path.is_dir():
            continue
        if (path / "data.yaml").exists():
            candidates.append(path)
        elif (path / "images" / "train").exists() and (path / "labels" / "train").exists():
            candidates.append(path)

    if not candidates:
        raise FileNotFoundError(
            "Cannot find YOLO dataset root. Expected data.yaml or images/train + labels/train."
        )

    candidates.sort(key=lambda item: len(item.parts))
    root = candidates[0]
    print(f"[DATASET] Root: {root}")
    return root


def write_data_yaml(dataset_root: Path) -> Path:
    data_yaml = dataset_root / "data.yaml"
    if data_yaml.exists() and PRESERVE_EXISTING_DATA_YAML:
        print(f"[DATASET] Using existing data.yaml: {data_yaml}")
        return data_yaml

    has_test = (dataset_root / "images" / "test").exists()
    lines = [
        f"path: {dataset_root}",
        "train: images/train",
        "val: images/val",
    ]
    if has_test:
        lines.append("test: images/test")
    lines.extend(
        [
            f"nc: {len(CLASS_NAMES)}",
            "names:",
            *[f"  {index}: {name}" for index, name in enumerate(CLASS_NAMES)],
            "",
        ]
    )
    data_yaml.write_text("\n".join(lines), encoding="utf-8")
    print(f"[DATASET] Wrote Kaggle data.yaml: {data_yaml}")
    return data_yaml


def image_files(split_dir: Path) -> list[Path]:
    if not split_dir.exists():
        return []
    return sorted(path for path in split_dir.rglob("*") if path.suffix.lower() in IMAGE_SUFFIXES)


def label_for_image(dataset_root: Path, image_path: Path) -> Path:
    relative = image_path.relative_to(dataset_root / "images")
    return dataset_root / "labels" / relative.with_suffix(".txt")


def validate_label_line(line: str, label_path: Path, line_no: int) -> None:
    parts = line.strip().split()
    if len(parts) != 5:
        raise ValueError(f"{label_path}:{line_no} must have 5 values, got {len(parts)}")

    class_id = int(float(parts[0]))
    if class_id < 0 or class_id >= len(CLASS_NAMES):
        raise ValueError(f"{label_path}:{line_no} invalid class id {class_id}")

    coords = [float(value) for value in parts[1:]]
    if any(value < 0.0 or value > 1.0 for value in coords):
        raise ValueError(f"{label_path}:{line_no} bbox values must be normalized in [0, 1]")
    if coords[2] <= 0 or coords[3] <= 0:
        raise ValueError(f"{label_path}:{line_no} width/height must be positive")


def move_bad_sample(dataset_root: Path, image_path: Path, label_path: Path, reason: str) -> None:
    split = image_path.relative_to(dataset_root / "images").parts[0]
    target_dir = INVALID_SAMPLE_DIR / split
    target_dir.mkdir(parents=True, exist_ok=True)

    for source in (image_path, label_path):
        if not source.exists():
            continue
        target = target_dir / source.name
        if target.exists():
            target.unlink()
        shutil.move(str(source), str(target))

    reason_file = target_dir / "invalid_reasons.txt"
    with reason_file.open("a", encoding="utf-8") as handle:
        handle.write(f"{image_path.name}\t{reason}\n")


def validate_dataset(dataset_root: Path) -> None:
    total_images = 0
    total_boxes = 0
    invalid_samples = []

    for split in ("train", "val"):
        images = image_files(dataset_root / "images" / split)
        if not images:
            raise FileNotFoundError(f"No images found for split: {split}")

        missing_labels = []
        empty_labels = []
        split_boxes = 0
        for image_path in images:
            label_path = label_for_image(dataset_root, image_path)
            if not label_path.exists():
                missing_labels.append(label_path)
                invalid_samples.append((image_path, label_path, "missing label file"))
                continue

            lines = [line for line in label_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if not lines:
                empty_labels.append(label_path)
                invalid_samples.append((image_path, label_path, "empty label file"))
                continue

            try:
                for line_no, line in enumerate(lines, start=1):
                    validate_label_line(line, label_path, line_no)
            except Exception as exc:
                invalid_samples.append((image_path, label_path, str(exc)))
                continue
            split_boxes += len(lines)

        if missing_labels:
            preview = "\n".join(str(path) for path in missing_labels[:10])
            print(f"[DATASET] Missing labels in {split}, first examples:\n{preview}")

        print(
            f"[DATASET] {split}: images={len(images)} boxes={split_boxes} "
            f"empty_label_files={len(empty_labels)}"
        )
        total_images += len(images)
        total_boxes += split_boxes

    if invalid_samples:
        report_path = WORK_DIR / "invalid_labels_report.txt"
        with report_path.open("w", encoding="utf-8") as handle:
            for image_path, label_path, reason in invalid_samples:
                handle.write(f"{image_path}\t{label_path}\t{reason}\n")

        print(f"[DATASET] Invalid samples: {len(invalid_samples)}")
        print(f"[DATASET] Report: {report_path}")
        print("[DATASET] First invalid samples:")
        for image_path, _label_path, reason in invalid_samples[:20]:
            print(f"  - {image_path.name}: {reason}")

        if INVALID_LABEL_POLICY == "skip_bad_samples":
            for image_path, label_path, reason in invalid_samples:
                move_bad_sample(dataset_root, image_path, label_path, reason)
            print(f"[DATASET] Moved invalid samples to: {INVALID_SAMPLE_DIR}")
        else:
            raise ValueError("Invalid labels found. Fix labels or set INVALID_LABEL_POLICY='skip_bad_samples'.")

    if total_boxes == 0:
        raise ValueError("Dataset has no bounding boxes.")
    print(f"[DATASET] OK: total_images={total_images} total_boxes={total_boxes}")


def preview_random_labels(dataset_root: Path, count: int = 8) -> None:
    from IPython.display import display
    from PIL import Image, ImageDraw

    images = image_files(dataset_root / "images" / "train")
    samples = random.sample(images, min(count, len(images)))
    for image_path in samples:
        label_path = label_for_image(dataset_root, image_path)
        image = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(image)
        width, height = image.size

        for line in label_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            _cls, xc, yc, bw, bh = [float(value) for value in line.split()]
            x1 = int((xc - bw / 2) * width)
            y1 = int((yc - bh / 2) * height)
            x2 = int((xc + bw / 2) * width)
            y2 = int((yc + bh / 2) * height)
            draw.rectangle((x1, y1, x2, y2), outline="red", width=3)

        print(image_path.name)
        display(image.resize((min(900, width), int(height * min(900, width) / width))))


# =============================================================================
# TRAIN / EVALUATE / EXPORT
# =============================================================================

def train_detector(data_yaml: Path) -> Path:
    from ultralytics import YOLO

    model = YOLO(BASE_MODEL)
    results = model.train(
        data=str(data_yaml),
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        patience=PATIENCE,
        seed=SEED,
        device=DEVICE,
        project=str(RUNS_DIR),
        name="license_plate_detector",
        exist_ok=True,
        optimizer="auto",
        cos_lr=True,
        close_mosaic=10,
        workers=WORKERS,
        plots=True,
    )

    best = Path(results.save_dir) / "weights" / "best.pt"
    if not best.exists():
        raise FileNotFoundError(f"best.pt not found: {best}")
    print(f"[TRAIN] Best checkpoint: {best}")
    return best


def validate_detector(best_pt: Path, data_yaml: Path) -> None:
    from ultralytics import YOLO

    model = YOLO(str(best_pt))
    model.val(data=str(data_yaml), imgsz=IMGSZ, conf=0.001, iou=0.6, plots=True)


def predict_samples(best_pt: Path, dataset_root: Path) -> None:
    from ultralytics import YOLO

    val_images = image_files(dataset_root / "images" / "val")
    if not val_images:
        return

    sample_dir = WORK_DIR / "predict_samples"
    sample_dir.mkdir(parents=True, exist_ok=True)
    for path in random.sample(val_images, min(24, len(val_images))):
        shutil.copy2(path, sample_dir / path.name)

    model = YOLO(str(best_pt))
    model.predict(
        source=str(sample_dir),
        imgsz=IMGSZ,
        conf=PREDICT_CONF,
        save=True,
        project=str(RUNS_DIR),
        name="predict_preview",
        exist_ok=True,
    )
    print(f"[PREDICT] Preview saved under: {RUNS_DIR / 'predict_preview'}")


def copy_outputs(best_pt: Path) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_best = OUTPUT_DIR / "license_plate_detector.pt"
    shutil.copy2(best_pt, output_best)
    print(f"[EXPORT] Copied best model to Kaggle output: {output_best}")

    results_dir = best_pt.parents[1]
    for filename in ("results.png", "confusion_matrix.png", "PR_curve.png", "F1_curve.png"):
        src = results_dir / filename
        if src.exists():
            shutil.copy2(src, OUTPUT_DIR / filename)

    if REPO_MODEL_OUTPUT.parent.exists():
        shutil.copy2(best_pt, REPO_MODEL_OUTPUT)
        print(f"[EXPORT] Copied best model to repo path: {REPO_MODEL_OUTPUT}")
    else:
        print(f"[EXPORT] Repo path not found, skipped: {REPO_MODEL_OUTPUT}")


def main() -> None:
    random.seed(SEED)
    install_dependencies()
    reset_work_dir()
    copy_dataset_source()

    dataset_root = find_dataset_root(DATASET_DIR)
    data_yaml = write_data_yaml(dataset_root)
    validate_dataset(dataset_root)

    # Recommended: run this cell once before training and visually check boxes.
    preview_random_labels(dataset_root, count=8)
    if STOP_AFTER_LABEL_PREVIEW:
        print("\nSTOP_AFTER_LABEL_PREVIEW=True")
        print("Training is paused so you can verify labels first.")
        print("If most red boxes do not cover the full license plate, fix/relabel the dataset.")
        print("After labels are correct, set STOP_AFTER_LABEL_PREVIEW=False and rerun.")
        return

    best_pt = train_detector(data_yaml)
    validate_detector(best_pt, data_yaml)
    predict_samples(best_pt, dataset_root)
    copy_outputs(best_pt)

    print("\nDONE")
    print("Use this file in backend:")
    print("  backend_v3/models/license_plate_detector.pt")
    print("Recommended runtime .env after copying model:")
    print("  PLATE_DETECTOR_MODEL=models/license_plate_detector.pt")
    print("  PLATE_DETECTOR_CONF=0.20")
    print("  PLATE_DETECTOR_IMGSZ=960")
    print("  PLATE_CROP_PADDING_RATIO=0.20")


if __name__ == "__main__":
    main()
