"""
Camera Bridge - Smart Parking edge worker.

Runtime flow:
RFID MQTT event -> ESP32-CAM burst capture -> YOLO plate detection ->
PaddleOCR plate text recognition -> FastAPI access decision endpoint.

Business ownership:
- This process does not create sessions, validate cards, calculate fee, or open
  the gate in full mode.
- FastAPI owns all parking decisions and publishes the OPEN command to ESP32.
"""

from __future__ import annotations

import gc
import json
import logging
import os
import queue
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np
import paho.mqtt.client as mqtt
import requests

# PaddlePaddle on Windows can fail inside OneDNN/MKLDNN fused_conv2d for
# PaddleOCR inference. Disable it before paddle/paddleocr is imported.
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_use_onednn", "0")


# ==============================================================================
# CONFIGURATION
# ==============================================================================

BACKEND_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    pass


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        logging.getLogger("camera_bridge").warning(
            "[CONFIG] Invalid integer %s, using default=%s", name, default
        )
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        logging.getLogger("camera_bridge").warning(
            "[CONFIG] Invalid float %s, using default=%s", name, default
        )
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


MQTT_BROKER = os.getenv("MQTT_BROKER", "127.0.0.1")
MQTT_PORT = _env_int("MQTT_PORT", 1883)
MQTT_KEEPALIVE = _env_int("MQTT_KEEPALIVE", 60)
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "CameraBridge")
MQTT_QOS = _env_int("MQTT_QOS", 1)
TOPIC_RFID = (
    os.getenv("MQTT_TOPIC_RFID")
    or os.getenv("MQTT_RFID_TOPIC")
    or "pbl5/smartparking/rfid_scanned"
)
TOPIC_GATE = (
    os.getenv("MQTT_TOPIC_GATE")
    or os.getenv("MQTT_GATE_TOPIC")
    or "pbl5/smartparking/gate"
)

ESP32_CAM_URL = os.getenv("ESP32_CAM_URL", "http://10.129.42.178/capture")
ESP32_CAM_CONNECT_TIMEOUT = _env_float("ESP32_CAM_CONNECT_TIMEOUT", 1.0)
ESP32_CAM_READ_TIMEOUT = _env_float("ESP32_CAM_READ_TIMEOUT", 4.0)
BURST_COUNT = _env_int("BURST_COUNT", 3)
BURST_INTERVAL_SEC = _env_float("BURST_INTERVAL_SEC", 0.2)
VEHICLE_CENTER_DELAY_SEC = _env_float("VEHICLE_CENTER_DELAY_SEC", 0.5)

BACKEND_API_BASE_URL = os.getenv("BACKEND_API_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")
BACKEND_ACCESS_EVENT_URL = os.getenv(
    "BACKEND_ACCESS_EVENT_URL",
    f"{BACKEND_API_BASE_URL}/access-events/rfid-camera",
)
BACKEND_CONNECT_TIMEOUT = _env_float("BACKEND_CONNECT_TIMEOUT", 2.0)
BACKEND_READ_TIMEOUT = _env_float("BACKEND_READ_TIMEOUT", 30.0)

CAMERA_BRIDGE_MODE = os.getenv("CAMERA_BRIDGE_MODE", "full").strip().lower()
if CAMERA_BRIDGE_MODE not in {"full", "capture_only"}:
    CAMERA_BRIDGE_MODE = "full"

GATE_ID = _env_int("GATE_ID", 1)
ACCESS_GATE_DIRECTION = os.getenv("ACCESS_GATE_DIRECTION", "auto").strip().lower()
if ACCESS_GATE_DIRECTION not in {"auto", "entry", "exit"}:
    ACCESS_GATE_DIRECTION = "auto"
GATE_OPEN_ON_CAPTURE_ONLY = _env_bool("GATE_OPEN_ON_CAPTURE_ONLY", False)

SAVE_DIR = os.getenv("CAPTURE_SAVE_DIR", str(BACKEND_DIR / "captured_images"))
CAPTURE_DIR = Path(SAVE_DIR)
CAPTURE_RETENTION_DAYS = _env_int("CAPTURE_RETENTION_DAYS", 7)
CAPTURE_IMAGE_MAX_BYTES = _env_int("CAPTURE_IMAGE_MAX_BYTES", 2_000_000)
STORE_CAPTURED_IMAGES_IN_DB = False
CAMERA_BRIDGE_DIRECT_DB_VALIDATION = False
CAPTURE_METADATA_COLLECTION = os.getenv("CAPTURE_METADATA_COLLECTION", "camera_captures")

MAX_QUEUE_SIZE = _env_int("CAMERA_BRIDGE_QUEUE_SIZE", 50)
RFID_COOLDOWN_SEC = _env_float("RFID_COOLDOWN_SEC", 2.0)

PLATE_DETECTOR_MODEL = os.getenv(
    "PLATE_DETECTOR_MODEL",
    str(BACKEND_DIR / "models" / "license_plate_detector.pt"),
)
PLATE_DETECTOR_CONF = _env_float("PLATE_DETECTOR_CONF", 0.35)
PLATE_DETECTOR_IMGSZ = _env_int("PLATE_DETECTOR_IMGSZ", 640)
PLATE_DETECTOR_CLASS_ID = _env_int("PLATE_DETECTOR_CLASS_ID", -1)
PLATE_DETECTOR_REQUIRED = _env_bool("PLATE_DETECTOR_REQUIRED", False)
PLATE_DETECTOR_FALLBACK_FULL_IMAGE = _env_bool("PLATE_DETECTOR_FALLBACK_FULL_IMAGE", True)
MAX_PLATE_DETECTIONS_PER_IMAGE = _env_int("MAX_PLATE_DETECTIONS_PER_IMAGE", 2)
PLATE_CROP_PADDING_RATIO = _env_float("PLATE_CROP_PADDING_RATIO", 0.08)

PADDLEOCR_LANG = os.getenv("PADDLEOCR_LANG", "en")
PADDLEOCR_USE_GPU = _env_bool("PADDLEOCR_USE_GPU", False)
PADDLEOCR_USE_ANGLE_CLS = _env_bool("PADDLEOCR_USE_ANGLE_CLS", False)
OCR_TIMEOUT_SEC = _env_float("OCR_TIMEOUT_SEC", 10.0)
OCR_ACCEPT_CONFIDENCE = _env_float("OCR_ACCEPT_CONFIDENCE", 0.45)
OCR_MIN_RETURN_CONFIDENCE = _env_float("OCR_MIN_RETURN_CONFIDENCE", 0.15)
OCR_MAX_IMAGES = _env_int("OCR_MAX_IMAGES", 3)
OCR_UPSCALE = _env_float("OCR_UPSCALE", 2.5)
OCR_MIN_WIDTH = _env_int("OCR_MIN_WIDTH", 300)
OCR_SAVE_DEBUG_CROPS = _env_bool("OCR_SAVE_DEBUG_CROPS", False)
OCR_DEBUG_DIR = Path(os.getenv("OCR_DEBUG_DIR", str(BACKEND_DIR / "captured_images" / "_ocr_debug")))

MAX_PROCESS_IMAGE_WIDTH = _env_int("MAX_PROCESS_IMAGE_WIDTH", 1200)
MIN_BLUR_SCORE = _env_float("MIN_BLUR_SCORE", 40.0)
CLAHE_CLIP_LIMIT = _env_float("OCR_CLAHE_CLIP_LIMIT", 2.0)
CLAHE_TILE_SIZE = _env_int("OCR_CLAHE_TILE_SIZE", 8)


# ==============================================================================
# LOGGING
# ==============================================================================


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[41m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        original_level = record.levelname
        color = self.COLORS.get(original_level, "")
        if color:
            record.levelname = f"{color}{original_level}{self.RESET}"
        try:
            return super().format(record)
        finally:
            record.levelname = original_level


logger = logging.getLogger("camera_bridge")
logger.setLevel(os.getenv("CAMERA_BRIDGE_LOG_LEVEL", "INFO").upper())
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(ColoredFormatter("[%(asctime)s] %(levelname)s - %(message)s"))
    logger.addHandler(handler)


# ==============================================================================
# DATA TYPES
# ==============================================================================


@dataclass(frozen=True)
class RFIDEvent:
    card_uid: str
    received_at: float


@dataclass
class PlateDetection:
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    source: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "bbox": [self.x1, self.y1, self.x2, self.y2],
            "confidence": round(float(self.confidence), 4),
            "source": self.source,
        }


@dataclass
class CapturedFrame:
    frame_no: int
    path: Path
    filename: str
    captured_at: datetime
    byte_size: int
    width: int
    height: int
    blur_score: float = 0.0
    brightness: float = 0.0
    contrast: float = 0.0
    glare_ratio: float = 0.0
    selected_for_ocr: bool = False
    detections: List[PlateDetection] = field(default_factory=list)
    selected_detection: Optional[PlateDetection] = None
    quality_score: float = 0.0


@dataclass
class CaptureBatch:
    card_uid: str
    capture_batch_id: str
    frames: List[CapturedFrame]


@dataclass
class ProcessingMetrics:
    rfid_received_at: float
    worker_started_at: float = 0.0
    vehicle_center_delay_started_at: float = 0.0
    vehicle_center_delay_finished_at: float = 0.0
    capture_started_at: float = 0.0
    capture_finished_at: float = 0.0
    ranking_started_at: float = 0.0
    ranking_finished_at: float = 0.0
    ocr_started_at: float = 0.0
    ocr_finished_at: float = 0.0
    backend_post_started_at: float = 0.0
    backend_post_finished_at: float = 0.0
    worker_finished_at: float = 0.0
    captured_frame_count: int = 0
    selected_ocr_frame_count: int = 0
    ocr_plate_found: bool = False
    backend_decision: Optional[str] = None
    backend_action: Optional[str] = None
    backend_open_gate: Optional[bool] = None
    backend_reason: Optional[str] = None


@dataclass
class PlateCandidate:
    plate: str
    confidence: float
    raw_text: str
    source: str


# Compatibility for old test controller.
task_queue: "queue.Queue[RFIDEvent]" = queue.Queue(maxsize=MAX_QUEUE_SIZE)
ocr_reader = None
db = None

_http = requests.Session()
_mqtt_client: Optional[mqtt.Client] = None
_processing_uids: set[str] = set()
_last_uid_at: Dict[str, float] = {}
_queue_lock = threading.Lock()


# ==============================================================================
# AI RESOURCES
# ==============================================================================


class PlateOcrRuntime:
    def __init__(self) -> None:
        self.detector: Optional[Any] = None
        self.paddle_ocr: Optional[Any] = None
        self.detector_loaded = False
        self.ocr_loaded = False
        self._lock = threading.Lock()

    def load(self) -> None:
        global ocr_reader
        if CAMERA_BRIDGE_MODE == "capture_only":
            logger.info("[MODE] capture_only: skipping YOLO/PaddleOCR load")
            return

        with self._lock:
            if self.ocr_loaded:
                return

            model_path = Path(PLATE_DETECTOR_MODEL)
            if model_path.exists():
                try:
                    from ultralytics import YOLO

                    logger.info("[YOLO] Loading plate detector: %s", model_path)
                    self.detector = YOLO(str(model_path))
                    self.detector_loaded = True
                    logger.info("[YOLO] Plate detector loaded")
                except Exception as exc:
                    logger.error("[YOLO] Failed to load plate detector: %s", exc)
                    if PLATE_DETECTOR_REQUIRED:
                        raise
            else:
                message = (
                    f"[YOLO] Plate detector not found: {model_path}. "
                    "Set PLATE_DETECTOR_MODEL to a trained license plate detector."
                )
                if PLATE_DETECTOR_REQUIRED:
                    raise FileNotFoundError(message)
                logger.warning(message)

            try:
                from paddleocr import PaddleOCR

                logger.info(
                    "[OCR] Loading PaddleOCR once: lang=%s gpu=%s angle_cls=%s",
                    PADDLEOCR_LANG,
                    PADDLEOCR_USE_GPU,
                    PADDLEOCR_USE_ANGLE_CLS,
                )
                kwargs = {
                    "lang": PADDLEOCR_LANG,
                    "use_angle_cls": PADDLEOCR_USE_ANGLE_CLS,
                    "use_gpu": PADDLEOCR_USE_GPU,
                    "show_log": False,
                    "enable_mkldnn": False,
                    "cpu_threads": 2,
                }
                try:
                    self.paddle_ocr = PaddleOCR(**kwargs)
                except TypeError:
                    kwargs.pop("show_log", None)
                    try:
                        self.paddle_ocr = PaddleOCR(**kwargs)
                    except TypeError:
                        kwargs.pop("enable_mkldnn", None)
                        kwargs.pop("cpu_threads", None)
                        self.paddle_ocr = PaddleOCR(**kwargs)
                self.ocr_loaded = True
                ocr_reader = self.paddle_ocr
                logger.info("[OCR] PaddleOCR loaded")
            except Exception as exc:
                logger.error("[OCR] PaddleOCR initialization failed: %s", exc)
                raise

    def detect_plates(self, image: np.ndarray) -> List[PlateDetection]:
        detections: List[PlateDetection] = []
        height, width = image.shape[:2]

        if self.detector is not None:
            try:
                results = self.detector.predict(
                    source=image,
                    conf=PLATE_DETECTOR_CONF,
                    imgsz=PLATE_DETECTOR_IMGSZ,
                    verbose=False,
                )
                for result in results:
                    if result.boxes is None:
                        continue
                    for box in result.boxes:
                        class_id = int(box.cls[0]) if box.cls is not None else -1
                        if PLATE_DETECTOR_CLASS_ID >= 0 and class_id != PLATE_DETECTOR_CLASS_ID:
                            continue
                        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                        conf = float(box.conf[0]) if box.conf is not None else 0.0
                        detections.append(
                            clamp_detection(
                                PlateDetection(x1, y1, x2, y2, conf, "yolo"),
                                width,
                                height,
                            )
                        )
            except Exception as exc:
                logger.error("[YOLO] Detection failed: %s", exc)

        if not detections and PLATE_DETECTOR_FALLBACK_FULL_IMAGE:
            detections.append(
                PlateDetection(
                    0,
                    0,
                    width,
                    height,
                    0.05,
                    "fallback_full_image",
                )
            )

        return sorted(
            detections,
            key=lambda item: (item.confidence, bbox_area(item)),
            reverse=True,
        )[:MAX_PLATE_DETECTIONS_PER_IMAGE]

    def read_text(self, image: np.ndarray) -> List[Tuple[str, float]]:
        if self.paddle_ocr is None:
            return []
        try:
            result = self.paddle_ocr.ocr(image, cls=PADDLEOCR_USE_ANGLE_CLS)
            return flatten_paddle_result(result)
        except Exception as exc:
            logger.error("[OCR] PaddleOCR read failed: %s", exc)
            return []


runtime = PlateOcrRuntime()


def init_resources() -> None:
    runtime.load()


# ==============================================================================
# NORMALIZATION
# ==============================================================================


VN_PLATE_RE = re.compile(r"^\d{2}[A-Z]{1,2}\d{4,6}$")
DIGIT_MAP = {
    "O": "0",
    "Q": "0",
    "D": "0",
    "I": "1",
    "L": "1",
    "|": "1",
    "Z": "2",
    "S": "5",
    "B": "8",
    "G": "6",
}
LETTER_MAP = {
    "0": "O",
    "1": "I",
    "2": "Z",
    "4": "A",
    "5": "S",
    "6": "G",
    "8": "B",
}


def normalize_uid(value: str) -> str:
    return (value or "").strip()


def map_digit(char: str) -> Optional[str]:
    char = char.upper()
    if char.isdigit():
        return char
    return DIGIT_MAP.get(char)


def map_letter(char: str) -> Optional[str]:
    char = char.upper()
    if "A" <= char <= "Z":
        return char
    return LETTER_MAP.get(char)


def is_valid_plate(value: str) -> bool:
    return bool(VN_PLATE_RE.match(value or ""))


def normalize_plate_text(raw_text: str) -> Optional[str]:
    candidates = extract_plate_candidates(raw_text, 1.0, "normalize")
    return candidates[0].plate if candidates else None


def extract_plate_candidates(raw_text: str, confidence: float, source: str) -> List[PlateCandidate]:
    if not raw_text:
        return []

    text = raw_text.upper()
    alnum = re.sub(r"[^0-9A-Z]", "", text)
    candidates: Dict[str, PlateCandidate] = {}

    def add(plate: str, penalty: float = 1.0) -> None:
        if not is_valid_plate(plate):
            return
        score = max(0.0, min(1.0, float(confidence) * penalty))
        current = candidates.get(plate)
        if current is None or score > current.confidence:
            candidates[plate] = PlateCandidate(
                plate=plate,
                confidence=score,
                raw_text=raw_text,
                source=source,
            )

    if is_valid_plate(alnum):
        add(alnum, 1.0)

    for length in range(7, min(10, len(alnum)) + 1):
        for start in range(0, len(alnum) - length + 1):
            chunk = alnum[start : start + length]
            for letter_count in (1, 2):
                digit_count = len(chunk) - 2 - letter_count
                if digit_count < 4 or digit_count > 6:
                    continue

                province = [map_digit(char) for char in chunk[:2]]
                letters = [map_letter(char) for char in chunk[2 : 2 + letter_count]]
                number = [map_digit(char) for char in chunk[2 + letter_count :]]
                if any(part is None for part in province + letters + number):
                    continue

                plate = "".join(province + letters + number)  # type: ignore[arg-type]
                replacement_penalty = 0.92 if plate != chunk else 1.0
                if start > 0 or length < len(alnum):
                    replacement_penalty *= 0.96
                add(plate, replacement_penalty)

    return sorted(candidates.values(), key=lambda item: item.confidence, reverse=True)


def flatten_paddle_result(result: Any) -> List[Tuple[str, float]]:
    output: List[Tuple[str, float]] = []

    def walk(node: Any) -> None:
        if node is None:
            return
        if isinstance(node, tuple) and len(node) >= 2 and isinstance(node[0], str):
            try:
                output.append((node[0], float(node[1])))
            except (TypeError, ValueError):
                output.append((node[0], 0.0))
            return
        if isinstance(node, (list, tuple)):
            if (
                len(node) >= 2
                and isinstance(node[1], (list, tuple))
                and len(node[1]) >= 2
                and isinstance(node[1][0], str)
            ):
                try:
                    output.append((node[1][0], float(node[1][1])))
                except (TypeError, ValueError):
                    output.append((node[1][0], 0.0))
                return
            for item in node:
                walk(item)

    walk(result)
    return output


# ==============================================================================
# IMAGE HELPERS
# ==============================================================================


def utcnow() -> datetime:
    return datetime.utcnow()


def monotonic_to_utc_iso(monotonic_value: float, reference_monotonic: float, reference_utc: datetime) -> Optional[str]:
    if monotonic_value <= 0:
        return None
    elapsed = monotonic_value - reference_monotonic
    return (reference_utc + timedelta(seconds=elapsed)).isoformat()


def elapsed_ms(start: float, end: float) -> Optional[int]:
    if start <= 0 or end <= 0:
        return None
    return int(round((end - start) * 1000))


def build_processing_metrics(metrics: ProcessingMetrics) -> Dict[str, Any]:
    reference_monotonic = metrics.worker_started_at or time.monotonic()
    reference_utc = utcnow() - timedelta(seconds=max(0.0, time.monotonic() - reference_monotonic))

    timestamps = {
        "rfid_received_at": monotonic_to_utc_iso(metrics.rfid_received_at, reference_monotonic, reference_utc),
        "worker_started_at": monotonic_to_utc_iso(metrics.worker_started_at, reference_monotonic, reference_utc),
        "vehicle_center_delay_started_at": monotonic_to_utc_iso(
            metrics.vehicle_center_delay_started_at,
            reference_monotonic,
            reference_utc,
        ),
        "vehicle_center_delay_finished_at": monotonic_to_utc_iso(
            metrics.vehicle_center_delay_finished_at,
            reference_monotonic,
            reference_utc,
        ),
        "capture_started_at": monotonic_to_utc_iso(metrics.capture_started_at, reference_monotonic, reference_utc),
        "capture_finished_at": monotonic_to_utc_iso(metrics.capture_finished_at, reference_monotonic, reference_utc),
        "ranking_started_at": monotonic_to_utc_iso(metrics.ranking_started_at, reference_monotonic, reference_utc),
        "ranking_finished_at": monotonic_to_utc_iso(metrics.ranking_finished_at, reference_monotonic, reference_utc),
        "ocr_started_at": monotonic_to_utc_iso(metrics.ocr_started_at, reference_monotonic, reference_utc),
        "ocr_finished_at": monotonic_to_utc_iso(metrics.ocr_finished_at, reference_monotonic, reference_utc),
        "backend_post_started_at": monotonic_to_utc_iso(
            metrics.backend_post_started_at,
            reference_monotonic,
            reference_utc,
        ),
        "backend_post_finished_at": monotonic_to_utc_iso(
            metrics.backend_post_finished_at,
            reference_monotonic,
            reference_utc,
        ),
        "worker_finished_at": monotonic_to_utc_iso(metrics.worker_finished_at, reference_monotonic, reference_utc),
    }

    durations = {
        "queue_wait_ms": elapsed_ms(metrics.rfid_received_at, metrics.worker_started_at),
        "vehicle_center_delay_ms": elapsed_ms(
            metrics.vehicle_center_delay_started_at,
            metrics.vehicle_center_delay_finished_at,
        ),
        "capture_ms": elapsed_ms(metrics.capture_started_at, metrics.capture_finished_at),
        "frame_ranking_ms": elapsed_ms(metrics.ranking_started_at, metrics.ranking_finished_at),
        "ocr_ms": elapsed_ms(metrics.ocr_started_at, metrics.ocr_finished_at),
        "backend_post_ms": elapsed_ms(metrics.backend_post_started_at, metrics.backend_post_finished_at),
        "end_to_end_ms": elapsed_ms(metrics.rfid_received_at, metrics.worker_finished_at),
        "decision_pipeline_ms": elapsed_ms(metrics.worker_started_at, metrics.backend_post_finished_at),
    }

    return {
        "timestamps": timestamps,
        "durations": durations,
        "counts": {
            "captured_frames": metrics.captured_frame_count,
            "selected_ocr_frames": metrics.selected_ocr_frame_count,
        },
        "ocr": {
            "plate_found": metrics.ocr_plate_found,
        },
        "backend": {
            "decision": metrics.backend_decision,
            "action": metrics.backend_action,
            "open_gate": metrics.backend_open_gate,
            "reason": metrics.backend_reason,
        },
        "config": {
            "burst_count": BURST_COUNT,
            "burst_interval_sec": BURST_INTERVAL_SEC,
            "vehicle_center_delay_sec": VEHICLE_CENTER_DELAY_SEC,
            "ocr_max_images": OCR_MAX_IMAGES,
            "ocr_timeout_sec": OCR_TIMEOUT_SEC,
            "plate_detector_conf": PLATE_DETECTOR_CONF,
            "plate_detector_fallback_full_image": PLATE_DETECTOR_FALLBACK_FULL_IMAGE,
            "backend_access_event_url": BACKEND_ACCESS_EVENT_URL,
            "esp32_cam_url": ESP32_CAM_URL,
        },
    }


def log_metrics_summary(uid: str, metrics: ProcessingMetrics) -> None:
    summary = build_processing_metrics(metrics)
    durations = summary["durations"]
    logger.info(
        "[METRICS] uid=%s queue=%sms capture=%sms rank=%sms ocr=%sms backend=%sms total=%sms frames=%s selected=%s",
        uid,
        durations.get("queue_wait_ms"),
        durations.get("capture_ms"),
        durations.get("frame_ranking_ms"),
        durations.get("ocr_ms"),
        durations.get("backend_post_ms"),
        durations.get("end_to_end_ms"),
        metrics.captured_frame_count,
        metrics.selected_ocr_frame_count,
    )


def safe_uid(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z_-]+", "_", value.strip()) or "unknown"


def bbox_area(detection: PlateDetection) -> int:
    return max(0, detection.x2 - detection.x1) * max(0, detection.y2 - detection.y1)


def clamp_detection(detection: PlateDetection, width: int, height: int) -> PlateDetection:
    x1 = max(0, min(detection.x1, width - 1))
    y1 = max(0, min(detection.y1, height - 1))
    x2 = max(x1 + 1, min(detection.x2, width))
    y2 = max(y1 + 1, min(detection.y2, height))
    return PlateDetection(x1, y1, x2, y2, detection.confidence, detection.source)


def expand_detection(detection: PlateDetection, width: int, height: int) -> PlateDetection:
    box_width = max(1, detection.x2 - detection.x1)
    box_height = max(1, detection.y2 - detection.y1)
    pad_x = int(box_width * PLATE_CROP_PADDING_RATIO)
    pad_y = int(box_height * PLATE_CROP_PADDING_RATIO)
    return clamp_detection(
        PlateDetection(
            detection.x1 - pad_x,
            detection.y1 - pad_y,
            detection.x2 + pad_x,
            detection.y2 + pad_y,
            detection.confidence,
            detection.source,
        ),
        width,
        height,
    )


def crop_detection(image: np.ndarray, detection: PlateDetection) -> np.ndarray:
    height, width = image.shape[:2]
    expanded = expand_detection(detection, width, height)
    return image[expanded.y1 : expanded.y2, expanded.x1 : expanded.x2]


def load_image(path: Path | str) -> Optional[np.ndarray]:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        logger.warning("[CAMERA] Failed to read image: %s", path)
        return None
    return image


def resize_for_processing(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    if width <= MAX_PROCESS_IMAGE_WIDTH:
        return image
    scale = MAX_PROCESS_IMAGE_WIDTH / float(width)
    return cv2.resize(image, (MAX_PROCESS_IMAGE_WIDTH, int(height * scale)), interpolation=cv2.INTER_AREA)


def calculate_quality(image: np.ndarray) -> Dict[str, float]:
    if image is None or image.size == 0:
        return {
            "blur_score": 0.0,
            "brightness": 0.0,
            "contrast": 0.0,
            "glare_ratio": 0.0,
        }

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    return {
        "blur_score": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
        "brightness": float(np.mean(gray)),
        "contrast": float(np.std(gray)),
        "glare_ratio": float(np.mean(gray > 245)),
    }


def ensure_bgr(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    return image


def upscale_for_ocr(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    if width >= OCR_MIN_WIDTH and OCR_UPSCALE <= 1.0:
        return image
    scale = max(OCR_UPSCALE, OCR_MIN_WIDTH / max(1, width))
    return cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_CUBIC)


def build_ocr_variants(plate_crop: np.ndarray) -> List[Tuple[str, np.ndarray]]:
    crop = upscale_for_ocr(plate_crop)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=(CLAHE_TILE_SIZE, CLAHE_TILE_SIZE))
    enhanced = clahe.apply(gray)
    denoised = cv2.bilateralFilter(enhanced, d=5, sigmaColor=45, sigmaSpace=45)
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(denoised, -1, sharpen_kernel)
    adaptive = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        7,
    )

    return [
        ("color", ensure_bgr(crop)),
        ("gray", ensure_bgr(gray)),
        ("clahe", ensure_bgr(denoised)),
        ("sharp", ensure_bgr(sharpened)),
        ("adaptive", ensure_bgr(adaptive)),
    ]


def preprocess_image(image_path: str) -> Optional[np.ndarray]:
    image = load_image(image_path)
    if image is None:
        return None
    detections = runtime.detect_plates(resize_for_processing(image))
    detection = detections[0] if detections else PlateDetection(0, 0, image.shape[1], image.shape[0], 0.0, "full")
    crop = crop_detection(image, detection)
    variants = build_ocr_variants(crop)
    return variants[2][1] if variants else crop


# ==============================================================================
# CAPTURE
# ==============================================================================


def ensure_capture_dir() -> None:
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    if OCR_SAVE_DEBUG_CROPS:
        OCR_DEBUG_DIR.mkdir(parents=True, exist_ok=True)


def cleanup_old_captures() -> None:
    if CAPTURE_RETENTION_DAYS <= 0 or not CAPTURE_DIR.exists():
        return
    cutoff = time.time() - CAPTURE_RETENTION_DAYS * 86400
    deleted = 0
    try:
        for path in CAPTURE_DIR.glob("*.jpg"):
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
                deleted += 1
        if deleted:
            logger.info("[CAMERA] Deleted old captures: %s", deleted)
    except OSError as exc:
        logger.warning("[CAMERA] Capture cleanup failed: %s", exc)


def decode_jpeg(content: bytes) -> Optional[np.ndarray]:
    buffer = np.frombuffer(content, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        return None
    return image


def capture_burst(card_uid: str) -> CaptureBatch:
    ensure_capture_dir()
    cleanup_old_captures()

    batch_timestamp = utcnow().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    capture_batch_id = f"{safe_uid(card_uid)}_{batch_timestamp}"
    frames: List[CapturedFrame] = []

    logger.info("[CAMERA] Capturing burst images: count=%s url=%s", BURST_COUNT, ESP32_CAM_URL)
    for frame_no in range(1, BURST_COUNT + 1):
        captured_at = utcnow()
        filename = f"{capture_batch_id}_frame{frame_no}.jpg"
        path = CAPTURE_DIR / filename
        try:
            response = _http.get(
                ESP32_CAM_URL,
                timeout=(ESP32_CAM_CONNECT_TIMEOUT, ESP32_CAM_READ_TIMEOUT),
            )
            response.raise_for_status()
            content = response.content

            if len(content) > CAPTURE_IMAGE_MAX_BYTES:
                logger.warning(
                    "[CAMERA] Frame %s too large for backend limit: %s bytes",
                    frame_no,
                    len(content),
                )

            image = decode_jpeg(content)
            if image is None:
                logger.error("[CAMERA] Frame %s decode failed", frame_no)
                continue

            path.write_bytes(content)
            height, width = image.shape[:2]
            frames.append(
                CapturedFrame(
                    frame_no=frame_no,
                    path=path,
                    filename=filename,
                    captured_at=captured_at,
                    byte_size=len(content),
                    width=width,
                    height=height,
                )
            )
            logger.info("[CAMERA] Saved frame %s: %s bytes=%s", frame_no, filename, len(content))
        except requests.Timeout:
            logger.error("[ERROR] Camera timeout on frame %s", frame_no)
        except requests.RequestException as exc:
            logger.error("[ERROR] Camera request failed on frame %s: %s", frame_no, exc)
        except OSError as exc:
            logger.error("[ERROR] Failed to save frame %s: %s", frame_no, exc)
        except Exception as exc:
            logger.exception("[ERROR] Unexpected capture error on frame %s: %s", frame_no, exc)

        if frame_no < BURST_COUNT:
            time.sleep(BURST_INTERVAL_SEC)

    return CaptureBatch(card_uid=card_uid, capture_batch_id=capture_batch_id, frames=frames)


def capture_burst_images(card_uid: str) -> List[str]:
    return [str(frame.path) for frame in capture_burst(card_uid).frames]


# ==============================================================================
# OCR PIPELINE
# ==============================================================================


def analyze_frame(frame: CapturedFrame) -> None:
    image = load_image(frame.path)
    if image is None:
        return

    image = resize_for_processing(image)
    detections = runtime.detect_plates(image)
    frame.detections = detections
    selected = detections[0] if detections else None
    frame.selected_detection = selected

    quality_target = crop_detection(image, selected) if selected else image
    quality = calculate_quality(quality_target)
    frame.blur_score = quality["blur_score"]
    frame.brightness = quality["brightness"]
    frame.contrast = quality["contrast"]
    frame.glare_ratio = quality["glare_ratio"]
    detector_bonus = selected.confidence * 100.0 if selected else 0.0
    frame.quality_score = frame.blur_score + detector_bonus

    logger.info(
        "[CAMERA] Quality %s blur=%.2f brightness=%.1f contrast=%.1f detector=%s score=%.2f",
        frame.filename,
        frame.blur_score,
        frame.brightness,
        frame.contrast,
        selected.source if selected else "none",
        frame.quality_score,
    )


def rank_frames_for_ocr(frames: Sequence[CapturedFrame]) -> List[CapturedFrame]:
    for frame in frames:
        analyze_frame(frame)
    ranked = sorted(frames, key=lambda item: item.quality_score, reverse=True)
    selected = ranked[: max(1, min(OCR_MAX_IMAGES, len(ranked)))]
    for frame in frames:
        frame.selected_for_ocr = frame in selected
    return selected


def save_debug_crop(frame: CapturedFrame, crop: np.ndarray, variant_name: str) -> None:
    if not OCR_SAVE_DEBUG_CROPS:
        return
    try:
        OCR_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        output = OCR_DEBUG_DIR / f"{Path(frame.filename).stem}_{variant_name}.jpg"
        cv2.imwrite(str(output), crop)
    except OSError as exc:
        logger.warning("[OCR] Failed to save debug crop: %s", exc)


def ocr_frame(frame: CapturedFrame, deadline: float) -> Optional[PlateCandidate]:
    image = load_image(frame.path)
    if image is None:
        return None
    image = resize_for_processing(image)

    detections = frame.detections or runtime.detect_plates(image)
    if not detections:
        logger.warning("[YOLO] No plate detection for %s", frame.filename)
        return None

    best: Optional[PlateCandidate] = None
    for det_index, detection in enumerate(detections[:MAX_PLATE_DETECTIONS_PER_IMAGE], start=1):
        if time.monotonic() >= deadline:
            logger.warning("[OCR] Timeout budget exceeded before detection %s", det_index)
            break

        crop = crop_detection(image, detection)
        if crop is None or crop.size == 0:
            continue

        save_debug_crop(frame, crop, f"det{det_index}_crop")
        variants = build_ocr_variants(crop)
        logger.info(
            "[OCR] Frame %s detection %s/%s source=%s conf=%.3f variants=%s",
            frame.frame_no,
            det_index,
            len(detections),
            detection.source,
            detection.confidence,
            len(variants),
        )

        for variant_name, variant_image in variants:
            if time.monotonic() >= deadline:
                logger.warning("[OCR] Timeout budget exceeded while reading variants")
                return best

            raw_items = runtime.read_text(variant_image)
            if not raw_items:
                continue

            raw_texts = [item[0] for item in raw_items]
            logger.info("[OCR] Raw %s/%s text=%s", frame.filename, variant_name, raw_texts)
            joined_text = " ".join(raw_texts)
            average_conf = sum(item[1] for item in raw_items) / max(1, len(raw_items))
            combined_conf = min(1.0, average_conf * max(0.2, detection.confidence))

            candidates: List[PlateCandidate] = []
            for text, conf in raw_items:
                candidates.extend(
                    extract_plate_candidates(
                        text,
                        min(1.0, conf * max(0.2, detection.confidence)),
                        f"{frame.filename}:{variant_name}:single",
                    )
                )
            candidates.extend(
                extract_plate_candidates(
                    joined_text,
                    combined_conf,
                    f"{frame.filename}:{variant_name}:joined",
                )
            )

            for candidate in candidates:
                logger.info(
                    "[OCR] Plate candidate: %s confidence=%.3f source=%s",
                    candidate.plate,
                    candidate.confidence,
                    candidate.source,
                )
                if best is None or candidate.confidence > best.confidence:
                    best = candidate
                if candidate.confidence >= OCR_ACCEPT_CONFIDENCE:
                    return candidate

    return best


def extract_plate_number_from_frames(
    frames: Sequence[CapturedFrame],
    timeout: float = OCR_TIMEOUT_SEC,
) -> Tuple[Optional[str], float]:
    if CAMERA_BRIDGE_MODE == "capture_only":
        return None, 0.0

    runtime.load()
    if not runtime.ocr_loaded:
        logger.error("[OCR] PaddleOCR is not loaded")
        return None, 0.0

    deadline = time.monotonic() + timeout
    best: Optional[PlateCandidate] = None
    for index, frame in enumerate(frames, start=1):
        if time.monotonic() >= deadline:
            logger.warning("[OCR] Timeout budget exceeded: %.1fs", timeout)
            break

        logger.info("[OCR] Reading image %s/%s: %s", index, len(frames), frame.filename)
        candidate = ocr_frame(frame, deadline)
        if candidate is None:
            continue
        if best is None or candidate.confidence > best.confidence:
            best = candidate
        if candidate.confidence >= OCR_ACCEPT_CONFIDENCE:
            logger.info("[OCR] Plate detected: %s confidence=%.3f", candidate.plate, candidate.confidence)
            return candidate.plate, candidate.confidence

    if best and best.confidence >= OCR_MIN_RETURN_CONFIDENCE:
        logger.warning(
            "[OCR] Returning low-confidence plate: %s confidence=%.3f",
            best.plate,
            best.confidence,
        )
        return best.plate, best.confidence

    if best:
        logger.warning(
            "[OCR] Ignoring low-confidence OCR candidate: %s confidence=%.3f min=%.3f",
            best.plate,
            best.confidence,
            OCR_MIN_RETURN_CONFIDENCE,
        )

    logger.error("[ERROR] OCR failed: no valid VN plate found")
    return None, 0.0


def extract_plate_number(image_paths: Sequence[str], timeout: float = OCR_TIMEOUT_SEC) -> Tuple[Optional[str], float]:
    frames: List[CapturedFrame] = []
    for index, path_value in enumerate(image_paths, start=1):
        path = Path(path_value)
        image = load_image(path)
        if image is None:
            continue
        height, width = image.shape[:2]
        frames.append(
            CapturedFrame(
                frame_no=index,
                path=path,
                filename=path.name,
                captured_at=utcnow(),
                byte_size=path.stat().st_size if path.exists() else 0,
                width=width,
                height=height,
            )
        )
    ranked = rank_frames_for_ocr(frames)
    return extract_plate_number_from_frames(ranked, timeout=timeout)


def build_frame_metadata(batch: CaptureBatch) -> List[Dict[str, Any]]:
    metadata = []
    for frame in batch.frames:
        selected = frame.selected_detection
        metadata.append(
            {
                "frame_no": frame.frame_no,
                "filename": frame.filename,
                "local_path": str(frame.path),
                "captured_at": frame.captured_at.isoformat(),
                "byte_size": frame.byte_size,
                "width": frame.width,
                "height": frame.height,
                "blur_score": round(frame.blur_score, 3),
                "brightness": round(frame.brightness, 3),
                "contrast": round(frame.contrast, 3),
                "glare_ratio": round(frame.glare_ratio, 5),
                "quality_score": round(frame.quality_score, 3),
                "selected_for_ocr": frame.selected_for_ocr,
                "selected_plate_bbox": selected.as_dict() if selected else None,
                "detections": [detection.as_dict() for detection in frame.detections],
                "plate_detector_model": PLATE_DETECTOR_MODEL,
                "plate_detector_loaded": runtime.detector_loaded,
                "ocr_engine": "paddleocr",
            }
        )
    return metadata


# ==============================================================================
# BACKEND AND MQTT
# ==============================================================================


def is_registration_mode_enabled() -> bool:
    try:
        response = _http.get(
            f"{BACKEND_API_BASE_URL}/rfid/registration-mode",
            timeout=(BACKEND_CONNECT_TIMEOUT, 3.0),
        )
        response.raise_for_status()
        data = response.json()
        return bool(data.get("success") and data.get("enabled"))
    except requests.RequestException as exc:
        logger.warning("[REGISTRATION] Failed to read registration mode: %s", exc)
        return False


def post_registration_scan(card_uid: str) -> Optional[Dict[str, Any]]:
    try:
        response = _http.post(
            f"{BACKEND_API_BASE_URL}/rfid/scan",
            json={"card_uid": card_uid, "gate_id": GATE_ID},
            timeout=(BACKEND_CONNECT_TIMEOUT, BACKEND_READ_TIMEOUT),
        )
        response.raise_for_status()
        result = response.json()
        logger.info(
            "[REGISTRATION] UID=%s action=%s already_registered=%s",
            card_uid,
            result.get("action"),
            result.get("already_registered"),
        )
        return result
    except requests.RequestException as exc:
        logger.error("[REGISTRATION] Failed to forward UID=%s: %s", card_uid, exc)
        return None


def post_access_event_to_backend(
    *,
    batch: CaptureBatch,
    plate_number: Optional[str],
    confidence: float,
    frame_metadata: Sequence[Dict[str, Any]],
    processing_metrics: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    opened_files = []
    files = []
    try:
        for frame in batch.frames:
            handle = frame.path.open("rb")
            opened_files.append(handle)
            files.append(("images", (frame.filename, handle, "image/jpeg")))

        data = {
            "card_uid": batch.card_uid,
            "gate_id": str(GATE_ID),
            "gate_direction": ACCESS_GATE_DIRECTION,
            "capture_batch_id": batch.capture_batch_id,
            "ocr_plate": plate_number or "",
            "ocr_confidence": f"{float(confidence):.4f}",
            "frame_metadata": json.dumps(list(frame_metadata), ensure_ascii=False),
            "processing_metrics": json.dumps(processing_metrics, ensure_ascii=False),
        }

        logger.info(
            "[BACKEND] Posting access event batch=%s images=%s plate=%s",
            batch.capture_batch_id,
            len(files),
            plate_number or "-",
        )
        response = _http.post(
            BACKEND_ACCESS_EVENT_URL,
            data=data,
            files=files,
            timeout=(BACKEND_CONNECT_TIMEOUT, BACKEND_READ_TIMEOUT),
        )
        response.raise_for_status()
        result = response.json()
        logger.info(
            "[BACKEND] Decision=%s action=%s open_gate=%s reason=%s",
            result.get("decision"),
            result.get("action"),
            result.get("open_gate"),
            result.get("reason", "-"),
        )
        return result
    except requests.Timeout:
        logger.error("[ERROR] Backend access-event timeout url=%s", BACKEND_ACCESS_EVENT_URL)
        return None
    except requests.RequestException as exc:
        status = getattr(exc.response, "status_code", None)
        body = getattr(exc.response, "text", "")
        logger.error("[ERROR] Backend access-event failed status=%s error=%s body=%s", status, exc, body[:500])
        return None
    except OSError as exc:
        logger.error("[ERROR] Failed to open captured images for backend upload: %s", exc)
        return None
    finally:
        for handle in opened_files:
            try:
                handle.close()
            except OSError:
                pass


def publish_gate_open_local() -> bool:
    if _mqtt_client is None:
        logger.error("[GATE] MQTT client is not ready")
        return False
    try:
        info = _mqtt_client.publish(TOPIC_GATE, "OPEN", qos=MQTT_QOS, retain=False)
        info.wait_for_publish(timeout=3.0)
        success = info.is_published()
        if success:
            logger.info("[GATE] OPEN command sent locally topic=%s", TOPIC_GATE)
        else:
            logger.error("[GATE] OPEN local publish timed out")
        return success
    except Exception as exc:
        logger.error("[GATE] OPEN local publish failed: %s", exc)
        return False


def parse_uid_payload(payload: bytes) -> str:
    text = payload.decode("utf-8", errors="ignore").strip()
    if not text:
        return ""
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return normalize_uid(str(value.get("uid") or value.get("card_uid") or ""))
    except json.JSONDecodeError:
        pass
    return normalize_uid(text)


def enqueue_uid(card_uid: str) -> bool:
    uid = normalize_uid(card_uid)
    if not uid:
        return False

    now = time.monotonic()
    with _queue_lock:
        if uid in _processing_uids:
            logger.warning("[MQTT] UID is already processing: %s", uid)
            return False
        last_seen = _last_uid_at.get(uid)
        if last_seen is not None and now - last_seen < RFID_COOLDOWN_SEC:
            logger.warning("[MQTT] UID cooldown active: %s %.2fs", uid, now - last_seen)
            return False
        try:
            task_queue.put_nowait(RFIDEvent(card_uid=uid, received_at=time.monotonic()))
            _last_uid_at[uid] = now
            logger.info("[MQTT] RFID queued uid=%s queue_size=%s", uid, task_queue.qsize())
            return True
        except queue.Full:
            logger.error("[MQTT] Queue full, dropping uid=%s", uid)
            return False


def mark_processing(uid: str) -> bool:
    with _queue_lock:
        if uid in _processing_uids:
            return False
        _processing_uids.add(uid)
        return True


def mark_done(uid: str) -> None:
    with _queue_lock:
        _processing_uids.discard(uid)


def process_rfid_event(event: RFIDEvent) -> None:
    uid = event.card_uid
    if not mark_processing(uid):
        logger.warning("[RFID] Duplicate processing skipped uid=%s", uid)
        return

    metrics = ProcessingMetrics(rfid_received_at=event.received_at)
    metrics.worker_started_at = time.monotonic()
    try:
        logger.info("=" * 80)
        logger.info("[RFID] UID received: %s", uid)
        if is_registration_mode_enabled():
            logger.info("[REGISTRATION] Registration mode active; skipping camera/OCR for uid=%s", uid)
            metrics.backend_post_started_at = time.monotonic()
            result = post_registration_scan(uid)
            metrics.backend_post_finished_at = time.monotonic()
            metrics.backend_decision = "registration"
            metrics.backend_action = result.get("action") if result else None
            metrics.backend_open_gate = False
            metrics.backend_reason = None if result else "registration_forward_failed"
            return

        metrics.vehicle_center_delay_started_at = time.monotonic()
        time.sleep(VEHICLE_CENTER_DELAY_SEC)
        metrics.vehicle_center_delay_finished_at = time.monotonic()

        metrics.capture_started_at = time.monotonic()
        batch = capture_burst(uid)
        metrics.capture_finished_at = time.monotonic()
        metrics.captured_frame_count = len(batch.frames)
        if not batch.frames:
            logger.error("[ERROR] Camera burst failed: no images captured")
            return

        if CAMERA_BRIDGE_MODE == "capture_only":
            logger.info("[MODE] capture_only: captured %s images, skipping OCR/backend", len(batch.frames))
            if GATE_OPEN_ON_CAPTURE_ONLY:
                logger.warning("[MODE] capture_only publishing OPEN locally")
                publish_gate_open_local()
            return

        metrics.ranking_started_at = time.monotonic()
        ranked_frames = rank_frames_for_ocr(batch.frames)
        metrics.ranking_finished_at = time.monotonic()
        metrics.selected_ocr_frame_count = len(ranked_frames)

        metrics.ocr_started_at = time.monotonic()
        plate_number, confidence = extract_plate_number_from_frames(ranked_frames, timeout=OCR_TIMEOUT_SEC)
        metrics.ocr_finished_at = time.monotonic()
        metrics.ocr_plate_found = bool(plate_number)
        if not plate_number:
            logger.warning("[OCR] No valid plate detected. Backend will apply fallback policy.")

        metadata = build_frame_metadata(batch)
        metrics.backend_post_started_at = time.monotonic()
        result = post_access_event_to_backend(
            batch=batch,
            plate_number=plate_number,
            confidence=confidence,
            frame_metadata=metadata,
            processing_metrics=build_processing_metrics(metrics),
        )
        metrics.backend_post_finished_at = time.monotonic()
        if result is None:
            logger.warning("[WARNING] Access rejected: backend unavailable")
        elif result.get("decision") == "accepted":
            metrics.backend_decision = result.get("decision")
            metrics.backend_action = result.get("action")
            metrics.backend_open_gate = result.get("open_gate")
            metrics.backend_reason = result.get("reason")
            logger.info("[ACCESS] Accepted action=%s session=%s", result.get("action"), result.get("session_id"))
        else:
            metrics.backend_decision = result.get("decision")
            metrics.backend_action = result.get("action")
            metrics.backend_open_gate = result.get("open_gate")
            metrics.backend_reason = result.get("reason")
            logger.warning("[WARNING] Access rejected: %s", result.get("reason", "unknown"))
    except Exception as exc:
        logger.exception("[ERROR] Worker failed for uid=%s: %s", uid, exc)
    finally:
        metrics.worker_finished_at = time.monotonic()
        log_metrics_summary(uid, metrics)
        mark_done(uid)
        gc.collect()
        logger.info("[RFID] Processing finished: %s", uid)
        logger.info("=" * 80)


# ==============================================================================
# MQTT CALLBACKS AND MAIN LOOP
# ==============================================================================


def on_connect(client: mqtt.Client, userdata: Any, flags: Dict[str, Any], rc: int) -> None:
    del userdata, flags
    if rc == 0:
        logger.info("[MQTT] Connected broker=%s:%s", MQTT_BROKER, MQTT_PORT)
        client.subscribe(TOPIC_RFID, qos=MQTT_QOS)
        logger.info("[MQTT] Subscribed topic=%s", TOPIC_RFID)
    else:
        logger.error("[MQTT] Connection failed rc=%s", rc)


def on_disconnect(client: mqtt.Client, userdata: Any, rc: int) -> None:
    del client, userdata
    if rc != 0:
        logger.warning("[MQTT] Unexpected disconnect rc=%s", rc)
    else:
        logger.info("[MQTT] Disconnected")


def on_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
    del client, userdata
    try:
        uid = parse_uid_payload(msg.payload)
        if not uid:
            logger.warning("[MQTT] Empty RFID payload ignored topic=%s", msg.topic)
            return
        enqueue_uid(uid)
    except Exception as exc:
        logger.exception("[MQTT] Failed to handle message: %s", exc)


def worker_loop() -> None:
    logger.info("[WORKER] Worker thread started")
    while True:
        try:
            event = task_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            process_rfid_event(event)
        finally:
            task_queue.task_done()


def build_mqtt_client() -> mqtt.Client:
    client = mqtt.Client(client_id=MQTT_CLIENT_ID, clean_session=True)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=15)
    return client


def main() -> None:
    global _mqtt_client

    logger.info("[SYSTEM] Camera Bridge starting")
    logger.info("[SYSTEM] MQTT broker=%s:%s", MQTT_BROKER, MQTT_PORT)
    logger.info("[SYSTEM] RFID topic=%s gate topic=%s", TOPIC_RFID, TOPIC_GATE)
    logger.info("[SYSTEM] ESP32-CAM=%s", ESP32_CAM_URL)
    logger.info("[SYSTEM] Backend access event URL=%s", BACKEND_ACCESS_EVENT_URL)
    logger.info("[SYSTEM] Captured images dir=%s", SAVE_DIR)
    logger.info(
        "[SYSTEM] Mode=%s gate_direction=%s detector=%s detector_required=%s fallback_full=%s",
        CAMERA_BRIDGE_MODE,
        ACCESS_GATE_DIRECTION,
        PLATE_DETECTOR_MODEL,
        PLATE_DETECTOR_REQUIRED,
        PLATE_DETECTOR_FALLBACK_FULL_IMAGE,
    )

    ensure_capture_dir()
    init_resources()

    worker = threading.Thread(target=worker_loop, name="camera-bridge-worker", daemon=False)
    worker.start()

    _mqtt_client = build_mqtt_client()
    try:
        _mqtt_client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
        _mqtt_client.loop_forever()
    except KeyboardInterrupt:
        logger.info("[SYSTEM] Stopping camera bridge")
    except Exception as exc:
        logger.exception("[SYSTEM] Fatal MQTT error: %s", exc)
        raise
    finally:
        try:
            _mqtt_client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
