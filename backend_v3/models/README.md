# Smart Parking AI Models

Place the trained license plate detector here. This folder is runtime-only.

Expected default file:

```text
license_plate_detector.pt
```

`camera_bridge.py` uses this model through:

```text
PLATE_DETECTOR_MODEL=models/license_plate_detector.pt
```

The model must detect the whole license plate box. PaddleOCR reads text only
after YOLO crops the detected plate region.

Training is intentionally kept outside this backend project so runtime code,
datasets, debug images, and training artifacts do not get mixed together.

```powershell
cd D:\PBL5\PBL5-PlateTrainer
.\install_deps.bat
.\train_plate_detector.bat
```

The trainer copies the final model to:

```text
D:\PBL5\PBL5-SmartParking_ESP32\backend_v3\models\license_plate_detector.pt
```

Install backend runtime dependencies with:

```powershell
cd D:\PBL5\PBL5-SmartParking_ESP32
.\scripts\install_backend_runtime.bat
```

`paddleocr` is installed with `--no-deps` because its full dependency set pulls
PDF/docx packages such as old PyMuPDF builds that are not needed for parking
camera images and are fragile on Windows/Python 3.11.

The current `car_long` and `CarTGMT` image folders do not provide real YOLO
bbox labels. The external trainer can generate pseudo-labels for bootstrap
training, but debug samples must be reviewed before production use.
