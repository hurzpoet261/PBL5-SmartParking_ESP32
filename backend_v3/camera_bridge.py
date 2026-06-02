"""
Camera Bridge - Smart Parking OCR and MQTT gate control.

Runtime flow:
RFID event from MQTT -> burst capture ESP32-CAM -> OpenCV preprocess ->
EasyOCR plate extraction -> backend business decision -> targeted MQTT command.
"""

from __future__ import annotations

import gc
import json
import logging
import os
import queue
import re
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
from gridfs import GridFS
import numpy as np
import paho.mqtt.client as mqtt
import requests
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database
from pymongo.errors import (
    ExecutionTimeout,
    OperationFailure,
    PyMongoError,
    ServerSelectionTimeoutError,
)


# ==============================================================================
# PROJECT IMPORTS
# ==============================================================================
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    # Import through the app database module to stay aligned with backend_v3 structure.
    # The FastAPI MongoDB manager itself is async Motor; this standalone MQTT worker
    # uses PyMongo below with strict timeouts to avoid event-loop coupling.
    from app.database import mongodb as app_mongodb

    settings = app_mongodb.settings
except Exception as exc:  # pragma: no cover - startup visibility
    settings = None
    print(f"[ERROR] Failed to load app settings: {exc}")


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
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        original_level = record.levelname
        color = self.COLORS.get(original_level, self.COLORS["RESET"])
        record.levelname = f"{color}{original_level}{self.COLORS['RESET']}"
        try:
            return super().format(record)
        finally:
            record.levelname = original_level


logger = logging.getLogger("camera_bridge")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(ColoredFormatter("[%(asctime)s] %(levelname)s - %(message)s"))
    logger.addHandler(handler)


# ==============================================================================
# CONFIGURATION
# ==============================================================================
def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        logger.warning("[CONFIG] Invalid integer for %s, using default=%s", name, default)
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        logger.warning("[CONFIG] Invalid float for %s, using default=%s", name, default)
        return default


MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = _env_int("MQTT_PORT", 1883)
MQTT_KEEPALIVE = _env_int("MQTT_KEEPALIVE", 60)
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "CameraBridge")
MQTT_QOS = _env_int("MQTT_QOS", 1)
TOPIC_RFID = os.getenv("MQTT_TOPIC_RFID", "pbl5/smartparking/rfid_scanned")
TOPIC_GATE_BASE = os.getenv("MQTT_TOPIC_GATE_BASE", "pbl5/smartparking/gate").rstrip("/")
DEFAULT_GATE_ID = _env_int("GATE_ID", 1)
DEFAULT_DEVICE_ID = os.getenv("GATE_DEVICE_ID", "esp32-gate-01").strip()

BACKEND_SCAN_URL = os.getenv(
    "BACKEND_SCAN_URL",
    "http://localhost:8000/api/v1/rfid/scan-with-ocr",
)
BACKEND_CONNECT_TIMEOUT = _env_float("BACKEND_CONNECT_TIMEOUT", 1.0)
BACKEND_READ_TIMEOUT = _env_float("BACKEND_READ_TIMEOUT", 5.0)

ESP32_CAM_URL = os.getenv("ESP32_CAM_URL", "http://192.168.1.208/capture")
ESP32_CAM_CONNECT_TIMEOUT = _env_float("ESP32_CAM_CONNECT_TIMEOUT", 1.0)
ESP32_CAM_READ_TIMEOUT = _env_float("ESP32_CAM_READ_TIMEOUT", 3.0)
BURST_COUNT = _env_int("BURST_COUNT", 3)
BURST_INTERVAL_SEC = _env_float("BURST_INTERVAL_SEC", 0.2)

SAVE_DIR = os.getenv("CAPTURE_SAVE_DIR", str(BACKEND_DIR / "captured_images"))
CAPTURE_DIR = Path(SAVE_DIR)
CAPTURE_RETENTION_DAYS = _env_int("CAPTURE_RETENTION_DAYS", 7)
STORE_CAPTURED_IMAGES_IN_DB = os.getenv("STORE_CAPTURED_IMAGES_IN_DB", "true").lower() == "true"
CAPTURE_IMAGE_BUCKET = os.getenv("CAPTURE_IMAGE_BUCKET", "camera_images")
CAPTURE_METADATA_COLLECTION = os.getenv("CAPTURE_METADATA_COLLECTION", "camera_captures")
CAPTURE_IMAGE_MAX_BYTES = _env_int("CAPTURE_IMAGE_MAX_BYTES", 2_000_000)

MAX_QUEUE_SIZE = _env_int("CAMERA_BRIDGE_QUEUE_SIZE", 50)
VEHICLE_CENTER_DELAY_SEC = _env_float("VEHICLE_CENTER_DELAY_SEC", 0.5)
CAMERA_BRIDGE_MODE = os.getenv("CAMERA_BRIDGE_MODE", "full").strip().lower()

OCR_LANGS = [lang.strip() for lang in os.getenv("OCR_LANGS", "en").split(",") if lang.strip()]
OCR_GPU = os.getenv("OCR_GPU", "false").lower() == "true"
OCR_TIMEOUT_SEC = _env_float("OCR_TIMEOUT_SEC", 8.0)
OCR_ALLOWLIST = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-. "

MAX_IMAGE_WIDTH = _env_int("OCR_MAX_IMAGE_WIDTH", 1000)
CLAHE_CLIP_LIMIT = _env_float("OCR_CLAHE_CLIP_LIMIT", 2.0)
CLAHE_TILE_SIZE = _env_int("OCR_CLAHE_TILE_SIZE", 8)

DB_SERVER_SELECTION_TIMEOUT_MS = _env_int("DB_SERVER_SELECTION_TIMEOUT_MS", 3000)
DB_CONNECT_TIMEOUT_MS = _env_int("DB_CONNECT_TIMEOUT_MS", 3000)
DB_SOCKET_TIMEOUT_MS = _env_int("DB_SOCKET_TIMEOUT_MS", 3000)
DB_OPERATION_TIMEOUT_MS = _env_int("DB_OPERATION_TIMEOUT_MS", 1200)
DB_RECONNECT_INTERVAL_SEC = _env_float("DB_RECONNECT_INTERVAL_SEC", 15.0)

DEFAULT_MONGODB_URL = "mongodb://localhost:27017"
DEFAULT_DB_NAME = "smart_parking"
MONGODB_URL = settings.MONGODB_URL if settings else os.getenv("MONGODB_URL", DEFAULT_MONGODB_URL)
MONGODB_DB_NAME = settings.MONGODB_DB_NAME if settings else os.getenv("MONGODB_DB_NAME", DEFAULT_DB_NAME)


# ==============================================================================
# STATE
# ==============================================================================
task_queue: "queue.Queue[RFIDEvent]" = queue.Queue(maxsize=MAX_QUEUE_SIZE)
camera_session = requests.Session()

mqtt_client: Optional[mqtt.Client] = None
worker_thread: Optional[threading.Thread] = None
stop_event = threading.Event()

mongo_client: Optional[MongoClient] = None
db: Optional[Database] = None
image_fs: Optional[GridFS] = None
ocr_reader = None


def is_capture_only_mode() -> bool:
    return CAMERA_BRIDGE_MODE == "capture_only"


NORMALIZED_PLATE_RE = re.compile(r"^\d{2}[A-Z]{1,2}\d{4,6}$")
DEVICE_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class RFIDEvent:
    card_uid: str
    received_at: float
    gate_id: int = DEFAULT_GATE_ID
    device_id: str = DEFAULT_DEVICE_ID


@dataclass(frozen=True)
class PlateCandidate:
    plate_number: str
    confidence: float
    source: str


@dataclass(frozen=True)
class CapturedFrame:
    path: Path
    filename: str
    frame_no: int
    image_bytes: bytes
    captured_at: datetime


# ==============================================================================
# OCR MODEL
# ==============================================================================
def load_ocr_reader():
    """Load EasyOCR once. Never call this from the worker loop."""
    try:
        import easyocr

        logger.info("[OCR] Loading EasyOCR model once: langs=%s gpu=%s", OCR_LANGS, OCR_GPU)
        reader = easyocr.Reader(OCR_LANGS, gpu=OCR_GPU, verbose=False)
        logger.info("[OCR] EasyOCR model loaded")
        return reader
    except Exception as exc:
        logger.error("[ERROR] EasyOCR initialization failed: %s", exc)
        return None


if is_capture_only_mode():
    logger.info("[MODE] capture_only: skipping EasyOCR model load")
    ocr_reader = None
else:
    ocr_reader = load_ocr_reader()


# ==============================================================================
# DATABASE
# ==============================================================================
def mask_mongodb_url(url: str) -> str:
    if "@" not in url or ":" not in url:
        return url
    try:
        prefix, suffix = url.split("@", 1)
        scheme, user_pass = prefix.rsplit("//", 1)
        user = user_pass.split(":", 1)[0]
        return f"{scheme}//{user}:****@{suffix}"
    except Exception:
        return "<masked>"


class DatabaseValidator:
    def __init__(self, mongodb_url: str, db_name: str) -> None:
        self.mongodb_url = mongodb_url
        self.db_name = db_name
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.image_fs: Optional[GridFS] = None
        self._lock = threading.Lock()
        self._next_reconnect_at = 0.0
        self._indexes_ready = False

    def ensure_connected(self, force: bool = False) -> bool:
        global mongo_client, db, image_fs

        if self.db is not None and not force:
            return True

        now = time.monotonic()
        if not force and now < self._next_reconnect_at:
            return False

        with self._lock:
            if self.db is not None and not force:
                return True

            self._next_reconnect_at = now + DB_RECONNECT_INTERVAL_SEC
            try:
                self.close()
                masked_url = mask_mongodb_url(self.mongodb_url)
                logger.info("[DB] Connecting MongoDB: %s / %s", masked_url, self.db_name)

                self.client = MongoClient(
                    self.mongodb_url,
                    appname="smart-parking-camera-bridge",
                    serverSelectionTimeoutMS=DB_SERVER_SELECTION_TIMEOUT_MS,
                    connectTimeoutMS=DB_CONNECT_TIMEOUT_MS,
                    socketTimeoutMS=DB_SOCKET_TIMEOUT_MS,
                    retryWrites=True,
                )
                self.client.admin.command("ping")
                self.db = self.client[self.db_name]
                self.image_fs = GridFS(self.db, collection=CAPTURE_IMAGE_BUCKET)
                mongo_client = self.client
                db = self.db
                image_fs = self.image_fs
                self.ensure_capture_indexes()
                logger.info("[DB] MongoDB connected")
                return True

            except ServerSelectionTimeoutError as exc:
                logger.error("[ERROR] MongoDB timeout: %s", exc)
            except PyMongoError as exc:
                logger.error("[ERROR] MongoDB connection error: %s", exc)
            except Exception as exc:
                logger.error("[ERROR] Unexpected MongoDB connection error: %s", exc)

            self.client = None
            self.db = None
            self.image_fs = None
            mongo_client = None
            db = None
            image_fs = None
            return False

    def close(self) -> None:
        global mongo_client, db, image_fs

        if self.client is not None:
            try:
                self.client.close()
            except Exception as exc:
                logger.warning("[DB] Error while closing MongoDB client: %s", exc)

        self.client = None
        self.db = None
        self.image_fs = None
        self._indexes_ready = False
        mongo_client = None
        db = None
        image_fs = None

    def mark_disconnected(self) -> None:
        logger.warning("[DB] Marking MongoDB as disconnected")
        self.close()

    def ensure_capture_indexes(self) -> None:
        if self.db is None or self._indexes_ready:
            return

        try:
            self.db[CAPTURE_METADATA_COLLECTION].create_index(
                [("captured_at", DESCENDING)],
                background=True,
            )
            self.db[CAPTURE_METADATA_COLLECTION].create_index(
                [("card_uid", ASCENDING), ("captured_at", DESCENDING)],
                background=True,
            )
            self.db[CAPTURE_METADATA_COLLECTION].create_index(
                [("capture_batch_id", ASCENDING), ("frame_no", ASCENDING)],
                background=True,
            )
            self.db[f"{CAPTURE_IMAGE_BUCKET}.files"].create_index(
                [("metadata.card_uid", ASCENDING), ("uploadDate", DESCENDING)],
                background=True,
            )
            self.db[f"{CAPTURE_IMAGE_BUCKET}.files"].create_index(
                [("metadata.capture_batch_id", ASCENDING), ("metadata.frame_no", ASCENDING)],
                background=True,
            )
            self._indexes_ready = True
            logger.info("[DB] Capture image indexes ready")
        except PyMongoError as exc:
            logger.warning("[DB] Could not create capture image indexes: %s", exc)
        except Exception as exc:
            logger.warning("[DB] Unexpected capture index error: %s", exc)

    def save_capture_image(
        self,
        *,
        card_uid: str,
        capture_batch_id: str,
        frame: CapturedFrame,
    ) -> Optional[str]:
        if not STORE_CAPTURED_IMAGES_IN_DB:
            return None

        if not frame.image_bytes:
            logger.warning("[DB] Skip empty image frame=%s batch=%s", frame.frame_no, capture_batch_id)
            return None

        if len(frame.image_bytes) > CAPTURE_IMAGE_MAX_BYTES:
            logger.warning(
                "[DB] Skip oversized image frame=%s size=%s max=%s",
                frame.frame_no,
                len(frame.image_bytes),
                CAPTURE_IMAGE_MAX_BYTES,
            )
            return None

        if not self.ensure_connected():
            logger.error("[ERROR] Cannot store image: MongoDB unavailable")
            return None

        assert self.db is not None
        assert self.image_fs is not None

        metadata = {
            "card_uid": card_uid,
            "capture_batch_id": capture_batch_id,
            "frame_no": frame.frame_no,
            "captured_at": frame.captured_at,
            "source_url": ESP32_CAM_URL,
            "local_path": str(frame.path),
            "content_type": "image/jpeg",
            "byte_size": len(frame.image_bytes),
            "bridge_mode": CAMERA_BRIDGE_MODE,
        }

        try:
            file_id = self.image_fs.put(
                frame.image_bytes,
                filename=frame.filename,
                content_type="image/jpeg",
                metadata=metadata,
            )
            self.db[CAPTURE_METADATA_COLLECTION].insert_one(
                {
                    **metadata,
                    "filename": frame.filename,
                    "gridfs_file_id": file_id,
                    "stored_at": datetime.now(),
                }
            )
            logger.info("[DB] Stored image frame=%s file_id=%s", frame.frame_no, file_id)
            return str(file_id)
        except (ExecutionTimeout, OperationFailure) as exc:
            logger.error("[ERROR] MongoDB image store timeout/failure: %s", exc)
            return None
        except PyMongoError as exc:
            logger.error("[ERROR] MongoDB image store error: %s", exc)
            self.mark_disconnected()
            return None
        except Exception as exc:
            logger.error("[ERROR] Unexpected image store error: %s", exc)
            return None

    def validate_vehicle_ownership(self, card_uid: str, plate_number: str) -> Dict[str, Any]:
        if not self.ensure_connected():
            return {"is_valid": False, "error": "Database unavailable"}

        assert self.db is not None
        normalized_ocr_plate = normalize_plate(plate_number)
        if not is_valid_plate(normalized_ocr_plate):
            return {
                "is_valid": False,
                "error": "Invalid OCR plate format",
                "plate_number": normalized_ocr_plate,
            }

        try:
            card = self.db.rfid_cards.find_one(
                {"card_uid": card_uid, "status": "active"},
                {"_id": 0, "card_uid": 1, "customer_id": 1, "vehicle_id": 1, "status": 1},
                max_time_ms=DB_OPERATION_TIMEOUT_MS,
            )

            if not card:
                logger.warning("[DB] RFID card not found or inactive: %s", card_uid)
                return {"is_valid": False, "error": "RFID card not found or inactive"}

            vehicle_id = card.get("vehicle_id")
            customer_id = card.get("customer_id")
            if not vehicle_id or not customer_id:
                logger.warning("[DB] RFID binding incomplete: uid=%s", card_uid)
                return {"is_valid": False, "error": "RFID card binding incomplete"}

            vehicle = self.db.vehicles.find_one(
                {"vehicle_id": vehicle_id, "is_active": True},
                {"_id": 0, "vehicle_id": 1, "customer_id": 1, "plate_number": 1, "is_active": 1},
                max_time_ms=DB_OPERATION_TIMEOUT_MS,
            )

            if not vehicle:
                logger.warning("[DB] Vehicle not found or inactive: %s", vehicle_id)
                return {"is_valid": False, "error": "Vehicle not found or inactive"}

            stored_plate = normalize_plate(str(vehicle.get("plate_number", "")))
            if stored_plate != normalized_ocr_plate:
                logger.warning(
                    "[WARNING] Plate mismatch: uid=%s db=%s ocr=%s",
                    card_uid,
                    stored_plate,
                    normalized_ocr_plate,
                )
                return {
                    "is_valid": False,
                    "error": "Vehicle plate mismatch",
                    "vehicle_id": vehicle_id,
                    "customer_id": customer_id,
                    "stored_plate": stored_plate,
                    "ocr_plate": normalized_ocr_plate,
                }

            logger.info("[DB] Validation success: uid=%s plate=%s", card_uid, normalized_ocr_plate)
            return {
                "is_valid": True,
                "vehicle_id": vehicle_id,
                "customer_id": customer_id,
                "vehicle_info": vehicle,
                "plate_number": normalized_ocr_plate,
                "error": None,
            }

        except (ExecutionTimeout, OperationFailure) as exc:
            logger.error("[ERROR] MongoDB operation timeout/failure: %s", exc)
            return {"is_valid": False, "error": f"Database operation failed: {exc}"}
        except PyMongoError as exc:
            logger.error("[ERROR] MongoDB error: %s", exc)
            self.mark_disconnected()
            return {"is_valid": False, "error": f"Database error: {exc}"}
        except Exception as exc:
            logger.error("[ERROR] Unexpected DB validation error: %s", exc)
            return {"is_valid": False, "error": f"Unexpected DB validation error: {exc}"}


db_validator = DatabaseValidator(MONGODB_URL, MONGODB_DB_NAME)
if not is_capture_only_mode() or STORE_CAPTURED_IMAGES_IN_DB:
    db_validator.ensure_connected(force=True)
else:
    logger.info("[MODE] capture_only: skipping MongoDB startup connection")


# ==============================================================================
# IMAGE PREPROCESSING
# ==============================================================================
def preprocess_image(image_path: str) -> Optional[np.ndarray]:
    """
    Fast OCR-oriented preprocessing.

    Pipeline:
    read image -> resize if needed -> grayscale -> CLAHE -> denoise ->
    adaptive threshold only for low-quality lighting cases.
    """
    start = time.monotonic()
    path = Path(image_path)

    if not path.exists():
        logger.error("[ERROR] Image file missing: %s", path)
        return None

    try:
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            logger.error("[ERROR] Image read failed: %s", path)
            return None

        height, width = image.shape[:2]
        if width > MAX_IMAGE_WIDTH:
            scale = MAX_IMAGE_WIDTH / float(width)
            image = cv2.resize(image, (MAX_IMAGE_WIDTH, int(height * scale)), interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        tile = max(2, CLAHE_TILE_SIZE)
        clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=(tile, tile))
        enhanced = clahe.apply(gray)

        if enhanced.size <= 1_000_000:
            denoised = cv2.bilateralFilter(enhanced, d=5, sigmaColor=50, sigmaSpace=50)
        else:
            denoised = cv2.GaussianBlur(enhanced, (3, 3), 0)

        brightness = float(np.mean(gray))
        contrast = float(np.std(gray))
        glare_ratio = float(np.mean(gray > 245))

        needs_threshold = brightness < 80 or contrast < 38 or glare_ratio > 0.03
        if needs_threshold:
            processed = cv2.adaptiveThreshold(
                denoised,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                31,
                7,
            )
        else:
            processed = denoised

        elapsed = time.monotonic() - start
        logger.debug(
            "[CAMERA] Preprocessed %s in %.3fs brightness=%.1f contrast=%.1f glare=%.3f threshold=%s",
            path.name,
            elapsed,
            brightness,
            contrast,
            glare_ratio,
            needs_threshold,
        )
        return processed

    except cv2.error as exc:
        logger.error("[ERROR] OpenCV preprocessing error for %s: %s", path, exc)
    except Exception as exc:
        logger.error("[ERROR] Preprocessing failed for %s: %s", path, exc)
    return None


# ==============================================================================
# OCR AND PLATE NORMALIZATION
# ==============================================================================
def normalize_plate(value: str) -> str:
    """Normalize plate to DB-comparable format: uppercase alnum only."""
    if not value:
        return ""

    text = value.upper().strip()
    text = text.replace(" ", "")
    text = re.sub(r"[^0-9A-Z]", "", text)

    # Common OCR confusion in the two leading province digits.
    if len(text) >= 2:
        prefix = text[:2].replace("O", "0").replace("I", "1").replace("L", "1")
        text = prefix + text[2:]

    return text


def is_valid_plate(plate_number: str) -> bool:
    return bool(NORMALIZED_PLATE_RE.match(plate_number or ""))


def _bbox_sort_key(result: Sequence[Any]) -> Tuple[float, float]:
    try:
        bbox = result[0]
        min_x = min(point[0] for point in bbox)
        min_y = min(point[1] for point in bbox)
        return float(min_y), float(min_x)
    except Exception:
        return 0.0, 0.0


def _extract_candidates_from_ocr(results: Iterable[Sequence[Any]], image_name: str) -> List[PlateCandidate]:
    ordered = sorted(list(results), key=_bbox_sort_key)
    candidates: List[PlateCandidate] = []
    raw_texts: List[str] = []
    confidences: List[float] = []

    for item in ordered:
        try:
            raw_text = str(item[1])
            confidence = float(item[2]) if len(item) > 2 and item[2] is not None else 0.0
        except Exception:
            continue

        raw_texts.append(raw_text)
        confidences.append(confidence)

        normalized = normalize_plate(raw_text)
        if is_valid_plate(normalized):
            candidates.append(PlateCandidate(normalized, confidence, f"{image_name}:single"))

    if raw_texts:
        joined = normalize_plate("".join(raw_texts))
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        if is_valid_plate(joined):
            candidates.append(PlateCandidate(joined, avg_conf, f"{image_name}:joined"))

        compact = normalize_plate(" ".join(raw_texts))
        if compact != joined and is_valid_plate(compact):
            candidates.append(PlateCandidate(compact, avg_conf, f"{image_name}:compact"))

    return candidates


def extract_plate_number(image_paths: Sequence[str], timeout: float = OCR_TIMEOUT_SEC) -> Tuple[Optional[str], float]:
    """
    OCR up to three images sequentially. Stop at the first valid VN plate.
    Returns normalized plate number, e.g. 43A12345.
    """
    if ocr_reader is None:
        logger.error("[ERROR] OCR failed: EasyOCR model is not available")
        return None, 0.0

    started = time.monotonic()
    best_candidate: Optional[PlateCandidate] = None

    for idx, image_path in enumerate(image_paths, start=1):
        if time.monotonic() - started > timeout:
            logger.warning("[WARNING] OCR timeout budget exceeded: %.1fs", timeout)
            break

        path = Path(image_path)
        if not path.exists():
            logger.warning("[WARNING] OCR skipped missing image: %s", path)
            continue

        processed = None
        results = None
        try:
            logger.info("[OCR] Reading image %s/%s: %s", idx, len(image_paths), path.name)
            processed = preprocess_image(str(path))
            if processed is None:
                continue

            results = ocr_reader.readtext(
                processed,
                detail=1,
                paragraph=False,
                allowlist=OCR_ALLOWLIST,
                batch_size=1,
            )

            candidates = _extract_candidates_from_ocr(results, path.name)
            if candidates:
                candidate = max(candidates, key=lambda item: item.confidence)
                logger.info(
                    "[OCR] Plate detected: %s confidence=%.3f source=%s",
                    candidate.plate_number,
                    candidate.confidence,
                    candidate.source,
                )
                return candidate.plate_number, candidate.confidence

            raw_text = [str(item[1]) for item in results] if results else []
            logger.warning("[WARNING] No valid plate in %s OCR text=%s", path.name, raw_text)

        except Exception as exc:
            logger.error("[ERROR] OCR crash on %s: %s", path, exc)
        finally:
            del processed
            del results
            gc.collect()

    if best_candidate:
        return best_candidate.plate_number, best_candidate.confidence

    logger.error("[ERROR] OCR failed: no valid VN plate found")
    return None, 0.0


# ==============================================================================
# CAMERA CAPTURE
# ==============================================================================
def _safe_filename_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_-]", "", value)
    return token[:64] or "unknown"


def ensure_capture_dir() -> None:
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)


def cleanup_old_captures(retention_days: int = CAPTURE_RETENTION_DAYS) -> None:
    if retention_days <= 0 or not CAPTURE_DIR.exists():
        return

    cutoff = datetime.now() - timedelta(days=retention_days)
    deleted = 0
    try:
        for path in CAPTURE_DIR.glob("*.jpg"):
            modified = datetime.fromtimestamp(path.stat().st_mtime)
            if modified < cutoff:
                path.unlink(missing_ok=True)
                deleted += 1
        if deleted:
            logger.info("[CAMERA] Deleted %s old captured images", deleted)
    except Exception as exc:
        logger.warning("[CAMERA] Capture cleanup failed: %s", exc)


def store_captured_images_in_database(
    card_uid: str,
    capture_batch_id: str,
    frames: Sequence[CapturedFrame],
) -> int:
    if not STORE_CAPTURED_IMAGES_IN_DB:
        return 0

    if not frames:
        return 0

    stored = 0
    logger.info("[DB] Storing captured images: count=%s batch=%s", len(frames), capture_batch_id)

    for frame in frames:
        file_id = db_validator.save_capture_image(
            card_uid=card_uid,
            capture_batch_id=capture_batch_id,
            frame=frame,
        )
        if file_id:
            stored += 1

    if stored == len(frames):
        logger.info("[DB] Stored captured images successfully: %s/%s", stored, len(frames))
    elif stored > 0:
        logger.warning("[DB] Partial image store: %s/%s", stored, len(frames))
    else:
        logger.error("[ERROR] No captured images were stored in MongoDB")

    return stored


def capture_burst_images(card_uid: str) -> Tuple[List[str], str]:
    ensure_capture_dir()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    uid_token = _safe_filename_token(card_uid)
    capture_batch_id = f"{uid_token}_{timestamp}"
    saved_images: List[str] = []
    captured_frames: List[CapturedFrame] = []

    logger.info("[CAMERA] Capturing burst images: count=%s url=%s", BURST_COUNT, ESP32_CAM_URL)

    for frame_no in range(1, BURST_COUNT + 1):
        try:
            response = camera_session.get(
                ESP32_CAM_URL,
                timeout=(ESP32_CAM_CONNECT_TIMEOUT, ESP32_CAM_READ_TIMEOUT),
            )

            try:
                response.raise_for_status()
                if not response.content:
                    logger.warning("[CAMERA] Empty image response for frame %s", frame_no)
                    continue

                image_bytes = response.content
                filename = CAPTURE_DIR / f"{capture_batch_id}_frame{frame_no}.jpg"
                captured_at = datetime.now()
                filename.write_bytes(image_bytes)
                saved_images.append(str(filename))
                captured_frames.append(
                    CapturedFrame(
                        path=filename,
                        filename=filename.name,
                        frame_no=frame_no,
                        image_bytes=image_bytes,
                        captured_at=captured_at,
                    )
                )
                logger.info("[CAMERA] Saved frame %s: %s bytes=%s", frame_no, filename.name, len(image_bytes))
            finally:
                response.close()

        except requests.exceptions.Timeout:
            logger.error("[ERROR] Camera timeout on frame %s", frame_no)
        except requests.exceptions.RequestException as exc:
            logger.error("[ERROR] Camera request failed on frame %s: %s", frame_no, exc)
        except OSError as exc:
            logger.error("[ERROR] Failed to save camera frame %s: %s", frame_no, exc)
        except Exception as exc:
            logger.error("[ERROR] Unexpected camera error on frame %s: %s", frame_no, exc)

        if frame_no < BURST_COUNT:
            time.sleep(BURST_INTERVAL_SEC)

    if not saved_images:
        logger.error("[ERROR] Camera burst failed: no images captured")
    else:
        store_captured_images_in_database(card_uid, capture_batch_id, captured_frames)

    captured_frames.clear()
    return saved_images, capture_batch_id


# ==============================================================================
# DATABASE VALIDATION COMPATIBILITY API
# ==============================================================================
def verify_vehicle_ownership(card_uid: str, plate_number: str, timeout: float = 1.0) -> Dict[str, Any]:
    """Compatibility wrapper used by camera_bridge_controller test endpoint."""
    del timeout  # DB operation timeouts are controlled by DB_OPERATION_TIMEOUT_MS.
    logger.info("[DB] Validating UID=%s plate=%s", card_uid, normalize_plate(plate_number))
    return db_validator.validate_vehicle_ownership(card_uid, plate_number)


# ==============================================================================
# BACKEND DECISION AND GATE CONTROL
# ==============================================================================
def request_backend_decision(
    event: RFIDEvent,
    plate_number: str,
    confidence: float,
    capture_batch_id: str,
) -> Dict[str, Any]:
    """Ask the backend to perform the authoritative parking transaction."""

    payload = {
        "card_uid": event.card_uid,
        "gate_id": event.gate_id,
        "device_id": event.device_id,
        "ocr_plate": plate_number,
        "ocr_confidence": confidence,
        "capture_batch_id": capture_batch_id,
        "timestamp": event.received_at,
    }
    logger.info(
        "[BACKEND] Requesting decision uid=%s plate=%s gate=%s device=%s",
        event.card_uid,
        plate_number,
        event.gate_id,
        event.device_id,
    )

    try:
        response = camera_session.post(
            BACKEND_SCAN_URL,
            json=payload,
            timeout=(BACKEND_CONNECT_TIMEOUT, BACKEND_READ_TIMEOUT),
        )
        response.raise_for_status()
        decision = response.json()
        if not isinstance(decision, dict):
            return {
                "success": False,
                "allowed": False,
                "reason": "Backend returned an invalid response.",
            }
        logger.info(
            "[BACKEND] Decision allowed=%s action=%s reason=%s",
            decision.get("allowed"),
            decision.get("action"),
            decision.get("reason"),
        )
        return decision
    except requests.exceptions.Timeout:
        logger.error("[ERROR] Backend decision timeout: %s", BACKEND_SCAN_URL)
    except requests.exceptions.RequestException as exc:
        logger.error("[ERROR] Backend decision request failed: %s", exc)
    except ValueError as exc:
        logger.error("[ERROR] Backend decision JSON decode failed: %s", exc)
    except Exception as exc:
        logger.error("[ERROR] Unexpected backend decision error: %s", exc)

    return {
        "success": False,
        "allowed": False,
        "reason": "Backend decision unavailable.",
    }


def publish_gate_open(gate_command: Dict[str, Any]) -> bool:
    """Publish only a backend-issued OPEN command to its target gate device."""

    if mqtt_client is None:
        logger.error("[ERROR] Cannot publish gate OPEN: MQTT client is not initialized")
        return False

    command = str(gate_command.get("command") or "").upper()
    device_id = str(gate_command.get("device_id") or "").strip()
    gate_id = gate_command.get("gate_id")
    if (
        command != "OPEN"
        or not DEVICE_ID_RE.fullmatch(device_id)
        or gate_id is None
    ):
        logger.error("[ERROR] Invalid backend gate command: %s", gate_command)
        return False

    topic = f"{TOPIC_GATE_BASE}/{device_id}"
    payload = json.dumps(
        {
            "command": "OPEN",
            "gate_id": gate_id,
            "device_id": device_id,
        },
        separators=(",", ":"),
    )

    try:
        info = mqtt_client.publish(topic, payload, qos=MQTT_QOS, retain=False)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error("[ERROR] MQTT publish failed rc=%s topic=%s", info.rc, topic)
            return False

        info.wait_for_publish(timeout=2.0)
        logger.info("[GATE] Backend-approved OPEN sent topic=%s payload=%s", topic, payload)
        return True

    except Exception as exc:
        logger.error("[ERROR] MQTT publish OPEN failed: %s", exc)
        return False


def reject_access(reason: str) -> None:
    # Requirement: invalid flow must not publish DENY.
    logger.warning("[WARNING] Access rejected: %s", reason)


# ==============================================================================
# WORKER PROCESSING
# ==============================================================================
def process_rfid_event(event: RFIDEvent) -> None:
    card_uid = event.card_uid
    logger.info("=" * 80)
    logger.info("[RFID] UID received: %s", card_uid)

    saved_images: List[str] = []
    try:
        time.sleep(VEHICLE_CENTER_DELAY_SEC)

        saved_images, capture_batch_id = capture_burst_images(card_uid)
        if not saved_images:
            reject_access("camera capture failed")
            return

        if is_capture_only_mode():
            logger.info(
                "[MODE] capture_only: captured %s images, skipping backend authorization",
                len(saved_images),
            )
            return

        plate_number, confidence = extract_plate_number(saved_images, timeout=OCR_TIMEOUT_SEC)
        if not plate_number:
            reject_access("OCR failed")
            return

        logger.info("[OCR] Normalized plate: %s confidence=%.3f", plate_number, confidence)

        decision = request_backend_decision(
            event,
            plate_number,
            confidence,
            capture_batch_id,
        )
        if not decision.get("allowed"):
            reject_access(decision.get("reason", "backend denied access"))
            return

        gate_command = decision.get("gate_command")
        if not isinstance(gate_command, dict):
            reject_access("backend allowed access without a gate command")
            return

        if (
            gate_command.get("gate_id") != event.gate_id
            or str(gate_command.get("device_id") or "").strip() != event.device_id
        ):
            reject_access("backend gate command target does not match RFID event")
            return

        if not publish_gate_open(gate_command):
            reject_access("failed to publish backend gate command")

    except Exception as exc:
        logger.error("[ERROR] Worker event failed uid=%s error=%s", card_uid, exc)
    finally:
        saved_images.clear()
        gc.collect()
        logger.info("[RFID] Processing finished: %s", card_uid)
        logger.info("=" * 80)


def worker_process() -> None:
    logger.info("[WORKER] Worker thread started")

    while not stop_event.is_set():
        event: Optional[RFIDEvent] = None
        try:
            event = task_queue.get(timeout=1.0)
            process_rfid_event(event)

        except queue.Empty:
            continue
        except Exception as exc:
            logger.error("[ERROR] Worker loop error: %s", exc)
        finally:
            if event is not None:
                task_queue.task_done()

    logger.info("[WORKER] Worker thread stopped")


def start_worker() -> None:
    global worker_thread

    if worker_thread is not None and worker_thread.is_alive():
        return

    worker_thread = threading.Thread(target=worker_process, name="camera-bridge-worker", daemon=True)
    worker_thread.start()


# ==============================================================================
# MQTT CALLBACKS
# ==============================================================================
def on_connect(client: mqtt.Client, userdata: Any, flags: Dict[str, Any], rc: int) -> None:
    del userdata, flags

    if rc == 0:
        logger.info("[MQTT] Connected broker=%s:%s", MQTT_BROKER, MQTT_PORT)
        client.subscribe(TOPIC_RFID, qos=MQTT_QOS)
        logger.info("[MQTT] Subscribed topic=%s", TOPIC_RFID)
    else:
        logger.error("[ERROR] MQTT connection failed rc=%s", rc)


def on_disconnect(client: mqtt.Client, userdata: Any, rc: int) -> None:
    del client, userdata
    if rc != 0:
        logger.warning("[MQTT] Unexpected disconnect rc=%s. Paho will reconnect with backoff.", rc)
    else:
        logger.info("[MQTT] Disconnected cleanly")


def on_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
    del client, userdata

    try:
        payload_text = msg.payload.decode("utf-8", errors="ignore").strip()
        if not payload_text:
            logger.warning("[MQTT] Empty RFID payload ignored")
            return

        try:
            payload = json.loads(payload_text)
        except ValueError:
            # Compatibility for already-flashed legacy scanners.
            payload = {"card_uid": payload_text}

        if not isinstance(payload, dict):
            logger.warning("[MQTT] Invalid RFID payload ignored: %s", payload_text)
            return

        card_uid = str(payload.get("card_uid") or "").strip()
        if not card_uid:
            logger.warning("[MQTT] Empty RFID payload ignored")
            return

        event = RFIDEvent(
            card_uid=card_uid,
            received_at=time.time(),
            gate_id=int(payload.get("gate_id") or DEFAULT_GATE_ID),
            device_id=str(payload.get("device_id") or DEFAULT_DEVICE_ID).strip(),
        )
        task_queue.put_nowait(event)
        logger.info(
            "[MQTT] RFID queued uid=%s gate=%s device=%s queue_size=%s",
            event.card_uid,
            event.gate_id,
            event.device_id,
            task_queue.qsize(),
        )

    except queue.Full:
        logger.error("[ERROR] Queue full. Dropping RFID event from topic=%s", msg.topic)
    except Exception as exc:
        logger.error("[ERROR] MQTT message handling failed: %s", exc)


# ==============================================================================
# MAIN
# ==============================================================================
def build_mqtt_client() -> mqtt.Client:
    client = mqtt.Client(client_id=MQTT_CLIENT_ID, clean_session=True)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    return client


def main() -> None:
    global mqtt_client

    logger.info("[SYSTEM] Camera Bridge starting")
    logger.info("[SYSTEM] MQTT broker=%s:%s", MQTT_BROKER, MQTT_PORT)
    logger.info("[SYSTEM] RFID topic=%s gate topic base=%s", TOPIC_RFID, TOPIC_GATE_BASE)
    logger.info("[SYSTEM] Backend scan endpoint=%s", BACKEND_SCAN_URL)
    logger.info("[SYSTEM] ESP32-CAM=%s", ESP32_CAM_URL)
    logger.info("[SYSTEM] MongoDB=%s db=%s", mask_mongodb_url(MONGODB_URL), MONGODB_DB_NAME)
    logger.info("[SYSTEM] Captured images dir=%s", SAVE_DIR)
    logger.info(
        "[SYSTEM] Store captured images in DB=%s bucket=%s metadata=%s max_bytes=%s",
        STORE_CAPTURED_IMAGES_IN_DB,
        CAPTURE_IMAGE_BUCKET,
        CAPTURE_METADATA_COLLECTION,
        CAPTURE_IMAGE_MAX_BYTES,
    )
    logger.info("[SYSTEM] Mode=%s", CAMERA_BRIDGE_MODE)

    ensure_capture_dir()
    cleanup_old_captures()
    if not is_capture_only_mode() or STORE_CAPTURED_IMAGES_IN_DB:
        db_validator.ensure_connected(force=True)
    start_worker()

    mqtt_client = build_mqtt_client()

    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
        mqtt_client.loop_forever(retry_first_connection=False)

    except KeyboardInterrupt:
        logger.info("[SYSTEM] Stopped by user")
    except Exception as exc:
        logger.error("[ERROR] Camera Bridge runtime error: %s", exc)
    finally:
        stop_event.set()
        try:
            if mqtt_client is not None:
                mqtt_client.disconnect()
        except Exception as exc:
            logger.warning("[MQTT] Disconnect error: %s", exc)

        db_validator.close()
        camera_session.close()
        logger.info("[SYSTEM] Camera Bridge stopped")


if __name__ == "__main__":
    main()
