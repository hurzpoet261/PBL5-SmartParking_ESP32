"""
RFID + camera access decision controller.

The camera bridge is an edge worker. This controller owns the business decision:
store images, validate card/plate/session, update parking state, and open gate.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Union

import cv2
import numpy as np
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.controllers.rfid_controller import REGISTRATION_MODE
from app.database import get_database
from app.models.parking_slot import SlotStatus
from app.models.session import SessionStatus
from app.services.fee_calculator import FeeCalculator
from app.services.gate_mqtt import gate_mqtt_publisher
from app.services.parking_status import publish_parking_status_update
from app.utils.id_generator import generate_id
from app.utils.serializers import serialize_mongodb_document

logger = logging.getLogger(__name__)

router = APIRouter()

CAPTURE_IMAGE_BUCKET = os.getenv("CAPTURE_IMAGE_BUCKET", "camera_images")
CAPTURE_METADATA_COLLECTION = os.getenv("CAPTURE_METADATA_COLLECTION", "camera_captures")
CAPTURE_IMAGE_MAX_BYTES = int(os.getenv("CAPTURE_IMAGE_MAX_BYTES", "2000000"))
OCR_ENTRY_POLICY = settings.OCR_ENTRY_POLICY.strip().lower()
OCR_EXIT_POLICY = settings.OCR_EXIT_POLICY.strip().lower()
STRICT_OCR_BEFORE_GATE = settings.STRICT_OCR_BEFORE_GATE
ALLOW_ENTRY_ON_OCR_MISMATCH = settings.ALLOW_ENTRY_ON_OCR_MISMATCH
ALLOW_EXIT_ON_OCR_FAILED = settings.ALLOW_EXIT_ON_OCR_FAILED
ALLOW_EXIT_ON_OCR_MISMATCH = settings.ALLOW_EXIT_ON_OCR_MISMATCH
ALLOW_EXIT_ON_OCR_FUZZY_MATCH = settings.ALLOW_EXIT_ON_OCR_FUZZY_MATCH
OCR_FUZZY_MAX_DISTANCE = settings.OCR_FUZZY_MAX_DISTANCE
ENABLE_DEV_ACCESS_TOOLS = os.getenv("ENABLE_DEV_ACCESS_TOOLS", "false").lower() == "true"

NORMALIZED_PLATE_RE = re.compile(r"^\d{2}[A-Z]{1,2}\d{4,6}$")
VALID_GATE_DIRECTIONS = {"auto", "entry", "exit"}


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        logger.warning("[ACCESS] Invalid float env %s, using default=%s", name, default)
        return default


PLATE_ROI_X1 = env_float("PLATE_ROI_X1", 0.28)
PLATE_ROI_Y1 = env_float("PLATE_ROI_Y1", 0.24)
PLATE_ROI_X2 = env_float("PLATE_ROI_X2", 0.72)
PLATE_ROI_Y2 = env_float("PLATE_ROI_Y2", 0.52)
OCR_DEBUG_ROTATION = os.getenv("OCR_DEBUG_ROTATION", os.getenv("OCR_ROTATIONS", "0").split(",")[0]).strip().lower()


def utcnow() -> datetime:
    return datetime.utcnow()


def normalize_plate(value: str) -> str:
    if not value:
        return ""

    text = value.upper().strip()
    text = re.sub(r"[^0-9A-Z]", "", text)
    if len(text) >= 2:
        prefix = text[:2].replace("O", "0").replace("I", "1").replace("L", "1")
        text = prefix + text[2:]
    return text


def is_valid_plate(value: str) -> bool:
    return bool(NORMALIZED_PLATE_RE.match(value or ""))


def plate_edit_distance(left: str, right: str) -> int:
    left = left or ""
    right = right or ""
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            replace_cost = previous[j - 1] + (0 if left_char == right_char else 1)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


def is_fuzzy_plate_match(ocr_plate: str, expected_plate: str) -> bool:
    if not ocr_plate or not expected_plate:
        return False
    if ocr_plate == expected_plate:
        return True
    if abs(len(ocr_plate) - len(expected_plate)) > OCR_FUZZY_MAX_DISTANCE:
        return False
    return plate_edit_distance(ocr_plate, expected_plate) <= OCR_FUZZY_MAX_DISTANCE


def parse_frame_metadata(raw_value: str) -> List[Dict[str, Any]]:
    if not raw_value:
        return []
    try:
        value = json.loads(raw_value)
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        logger.warning("[ACCESS] Invalid frame_metadata JSON ignored")
        return []


def parse_processing_metrics(raw_value: str) -> Dict[str, Any]:
    if not raw_value:
        return {}
    try:
        value = json.loads(raw_value)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        logger.warning("[ACCESS] Invalid processing_metrics JSON ignored")
        return {}


def init_processing_metrics(worker_metrics: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "worker": worker_metrics,
        "backend": {
            "timestamps": {
                "request_received_at": utcnow().isoformat(),
            },
            "durations": {},
        },
    }


def backend_metric_section(metrics: Dict[str, Any]) -> Dict[str, Any]:
    backend = metrics.setdefault("backend", {})
    backend.setdefault("timestamps", {})
    backend.setdefault("durations", {})
    return backend


def mark_backend_timestamp(metrics: Dict[str, Any], name: str) -> None:
    backend_metric_section(metrics)["timestamps"][name] = utcnow().isoformat()


def set_backend_duration(metrics: Dict[str, Any], name: str, started_at: float) -> None:
    elapsed = int(round((time.perf_counter() - started_at) * 1000))
    backend_metric_section(metrics)["durations"][name] = elapsed


def frame_meta_at(metadata: Sequence[Dict[str, Any]], index: int) -> Dict[str, Any]:
    if index < len(metadata) and isinstance(metadata[index], dict):
        return metadata[index]
    return {}


def crop_plate_roi(image: np.ndarray) -> np.ndarray:
    if image is None or image.size == 0:
        return image

    height, width = image.shape[:2]
    x1 = int(max(0.0, min(PLATE_ROI_X1, 0.98)) * width)
    y1 = int(max(0.0, min(PLATE_ROI_Y1, 0.98)) * height)
    x2 = int(max(0.02, min(PLATE_ROI_X2, 1.0)) * width)
    y2 = int(max(0.02, min(PLATE_ROI_Y2, 1.0)) * height)

    if x2 <= x1 or y2 <= y1:
        return image

    return image[y1:y2, x1:x2]


def crop_detected_plate(image: np.ndarray, metadata: Optional[Dict[str, Any]]) -> np.ndarray:
    """Crop YOLO-detected plate from stored GridFS metadata when available."""
    if image is None or image.size == 0 or not metadata:
        return crop_plate_roi(image)

    selected = metadata.get("selected_plate_bbox")
    if not isinstance(selected, dict):
        return crop_plate_roi(image)

    bbox = selected.get("bbox")
    if not isinstance(bbox, list) or len(bbox) != 4:
        return crop_plate_roi(image)

    height, width = image.shape[:2]
    try:
        x1, y1, x2, y2 = [int(value) for value in bbox]
    except (TypeError, ValueError):
        return crop_plate_roi(image)

    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(x1 + 1, min(x2, width))
    y2 = max(y1 + 1, min(y2, height))
    return image[y1:y2, x1:x2]


def rotate_debug_image(image: np.ndarray) -> np.ndarray:
    if OCR_DEBUG_ROTATION in {"0", "none", "normal"}:
        return image
    if OCR_DEBUG_ROTATION in {"90cw", "cw", "right"}:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if OCR_DEBUG_ROTATION in {"90ccw", "ccw", "left"}:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if OCR_DEBUG_ROTATION in {"180", "flip"}:
        return cv2.rotate(image, cv2.ROTATE_180)
    return image


def calculate_image_quality(image: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if image is None or image.size == 0:
        return {
            "blur_score": 0.0,
            "brightness": 0.0,
            "contrast": 0.0,
            "glare_ratio": 0.0,
        }

    roi = crop_detected_plate(image, metadata)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    return {
        "blur_score": round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 3),
        "brightness": round(float(np.mean(gray)), 3),
        "contrast": round(float(np.std(gray)), 3),
        "glare_ratio": round(float(np.mean(gray > 245)), 5),
        "roi_shape": list(roi.shape),
    }


def preprocess_debug_image(image: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> np.ndarray:
    roi = crop_detected_plate(image, metadata)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    denoised = cv2.bilateralFilter(enhanced, d=5, sigmaColor=50, sigmaSpace=50)

    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    glare_ratio = float(np.mean(gray > 245))
    if brightness < 80 or contrast < 38 or glare_ratio > 0.03:
        return cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            7,
        )
    return denoised


def decode_image_bytes(content: bytes) -> np.ndarray:
    np_buffer = np.frombuffer(content, dtype=np.uint8)
    image = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=415, detail="Stored file is not a readable image")
    return image


def encode_image_response(image: np.ndarray, *, extension: str, media_type: str, headers: Dict[str, str]) -> Response:
    ok, encoded = cv2.imencode(extension, image)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode debug image")
    return Response(content=encoded.tobytes(), media_type=media_type, headers=headers)


async def read_gridfs_image_content(db: AsyncIOMotorDatabase, file_id: str):
    try:
        object_id = ObjectId(file_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid GridFS file id")

    bucket = AsyncIOMotorGridFSBucket(db, bucket_name=CAPTURE_IMAGE_BUCKET)
    try:
        grid_out = await bucket.open_download_stream(object_id)
        return await grid_out.read(), grid_out
    except Exception as exc:
        logger.warning("[ACCESS] Image not found file_id=%s error=%s", file_id, exc)
        raise HTTPException(status_code=404, detail="Image not found")


def normalize_gate_direction(value: str) -> str:
    direction = (value or "auto").strip().lower()
    if direction not in VALID_GATE_DIRECTIONS:
        raise HTTPException(status_code=400, detail="gate_direction must be auto, entry, or exit")
    return direction


async def store_uploaded_images(
    *,
    db: AsyncIOMotorDatabase,
    card_uid: str,
    gate_id: int,
    capture_batch_id: str,
    ocr_plate: str,
    ocr_confidence: float,
    frame_metadata: Sequence[Dict[str, Any]],
    images: Optional[Sequence[UploadFile]],
) -> List[Dict[str, Any]]:
    if not images:
        logger.warning("[ACCESS] No uploaded images received for batch=%s", capture_batch_id)
        return []

    bucket = AsyncIOMotorGridFSBucket(db, bucket_name=CAPTURE_IMAGE_BUCKET)
    stored: List[Dict[str, Any]] = []

    for idx, upload in enumerate(images):
        content = await upload.read()
        frame_no = int(frame_meta_at(frame_metadata, idx).get("frame_no") or idx + 1)

        if not content:
            logger.warning("[ACCESS] Empty image skipped frame=%s", frame_no)
            continue

        if len(content) > CAPTURE_IMAGE_MAX_BYTES:
            logger.warning(
                "[ACCESS] Oversized image skipped frame=%s size=%s max=%s",
                frame_no,
                len(content),
                CAPTURE_IMAGE_MAX_BYTES,
            )
            continue

        meta = frame_meta_at(frame_metadata, idx)
        filename = upload.filename or f"{capture_batch_id}_frame{frame_no}.jpg"
        captured_at = utcnow()
        metadata = {
            "card_uid": card_uid,
            "gate_id": gate_id,
            "capture_batch_id": capture_batch_id,
            "frame_no": frame_no,
            "captured_at": captured_at,
            "source_url": meta.get("source_url"),
            "local_path": meta.get("local_path"),
            "content_type": upload.content_type or "image/jpeg",
            "byte_size": len(content),
            "width": meta.get("width"),
            "height": meta.get("height"),
            "blur_score": meta.get("blur_score"),
            "brightness": meta.get("brightness"),
            "contrast": meta.get("contrast"),
            "glare_ratio": meta.get("glare_ratio"),
            "quality_score": meta.get("quality_score"),
            "selected_for_ocr": bool(meta.get("selected_for_ocr", False)),
            "selected_plate_bbox": meta.get("selected_plate_bbox"),
            "detections": meta.get("detections"),
            "plate_detector_model": meta.get("plate_detector_model"),
            "plate_detector_loaded": meta.get("plate_detector_loaded"),
            "ocr_engine": meta.get("ocr_engine"),
            "ocr_plate": ocr_plate,
            "ocr_confidence": ocr_confidence,
        }

        file_id = await bucket.upload_from_stream(
            filename,
            content,
            metadata=metadata,
        )

        capture_doc = {
            **metadata,
            "filename": filename,
            "gridfs_file_id": file_id,
            "stored_at": utcnow(),
            "view_url": f"/api/v1/access-events/images/{file_id}",
        }
        await db[CAPTURE_METADATA_COLLECTION].insert_one(capture_doc)
        stored.append(capture_doc)

    return stored


async def link_captures_to_decision(
    *,
    db: AsyncIOMotorDatabase,
    capture_batch_id: str,
    session_id: Optional[str],
    event_id: str,
    event_type: Optional[str],
    decision: str,
    reason: Optional[str],
) -> None:
    update = {
        "event_id": event_id,
        "session_id": session_id,
        "event_type": event_type,
        "decision": decision,
        "reject_reason": reason,
        "updated_at": utcnow(),
    }
    await db[CAPTURE_METADATA_COLLECTION].update_many(
        {"capture_batch_id": capture_batch_id},
        {"$set": update},
    )
    await db[f"{CAPTURE_IMAGE_BUCKET}.files"].update_many(
        {"metadata.capture_batch_id": capture_batch_id},
        {"$set": {f"metadata.{key}": value for key, value in update.items()}},
    )


def normalize_uploaded_images(
    images: Optional[Union[UploadFile, Sequence[UploadFile]]],
) -> List[UploadFile]:
    def is_upload_file(value: Any) -> bool:
        return hasattr(value, "read") and hasattr(value, "filename")

    if images is None:
        return []
    if is_upload_file(images):
        return [images]  # type: ignore[list-item]
    if isinstance(images, (list, tuple)):
        return [item for item in images if is_upload_file(item)]  # type: ignore[list-item]
    return []


async def record_parking_event(db: AsyncIOMotorDatabase, event_doc: Dict[str, Any]) -> Dict[str, Any]:
    for attempt in range(3):
        try:
            await db.parking_events.insert_one(event_doc)
            return serialize_mongodb_document(event_doc)
        except DuplicateKeyError as exc:
            if "event_id" not in str(exc) or attempt >= 2:
                raise
            event_doc["event_id"] = await generate_id(db, "parking_events", "E")
            logger.warning("[ACCESS] Duplicate event_id detected, regenerated=%s", event_doc["event_id"])

    raise RuntimeError("Failed to record parking event")


def build_event_doc(
    *,
    event_id: str,
    card_uid: str,
    gate_id: int,
    capture_batch_id: str,
    action: Optional[str],
    decision: str,
    reason: Optional[str],
    ocr_plate: str,
    ocr_confidence: float,
    expected_plate: Optional[str],
    session_id: Optional[str],
    customer_id: Optional[str],
    vehicle_id: Optional[str],
    image_ids: Sequence[str],
    gate_open_sent: bool,
    review_required: bool,
    processing_metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    event_doc = {
        "event_id": event_id,
        "card_uid": card_uid,
        "gate_id": gate_id,
        "capture_batch_id": capture_batch_id,
        "event_type": action,
        "decision": decision,
        "reason": reason,
        "ocr_plate": ocr_plate,
        "ocr_confidence": ocr_confidence,
        "expected_plate": expected_plate,
        "session_id": session_id,
        "customer_id": customer_id,
        "vehicle_id": vehicle_id,
        "image_ids": list(image_ids),
        "gate_open_sent": gate_open_sent,
        "review_required": review_required,
        "created_at": utcnow(),
    }
    if processing_metrics:
        event_doc["processing_metrics"] = processing_metrics
    return event_doc


async def reject_event(
    *,
    db: AsyncIOMotorDatabase,
    card_uid: str,
    gate_id: int,
    capture_batch_id: str,
    reason: str,
    ocr_plate: str,
    ocr_confidence: float,
    expected_plate: Optional[str],
    customer_id: Optional[str],
    vehicle_id: Optional[str],
    image_ids: Sequence[str],
    action: Optional[str] = None,
    processing_metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if processing_metrics:
        mark_backend_timestamp(processing_metrics, "decision_finished_at")
    event_id = await generate_id(db, "parking_events", "E")
    event_doc = build_event_doc(
        event_id=event_id,
        card_uid=card_uid,
        gate_id=gate_id,
        capture_batch_id=capture_batch_id,
        action=action,
        decision="rejected",
        reason=reason,
        ocr_plate=ocr_plate,
        ocr_confidence=ocr_confidence,
        expected_plate=expected_plate,
        session_id=None,
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        image_ids=image_ids,
        gate_open_sent=False,
        review_required=True,
        processing_metrics=processing_metrics,
    )
    await record_parking_event(db, event_doc)
    await link_captures_to_decision(
        db=db,
        capture_batch_id=capture_batch_id,
        session_id=None,
        event_id=event_id,
        event_type=action,
        decision="rejected",
        reason=reason,
    )
    return {
        "success": False,
        "decision": "rejected",
        "action": action,
        "reason": reason,
        "open_gate": False,
        "event": serialize_mongodb_document(event_doc),
    }


async def publish_open_gate() -> bool:
    return await asyncio.to_thread(gate_mqtt_publisher.publish_open)


async def find_vehicle_by_normalized_plate(
    db: AsyncIOMotorDatabase,
    normalized_plate: str,
) -> Optional[Dict[str, Any]]:
    direct_match = await db.vehicles.find_one({"plate_number": normalized_plate})
    if direct_match:
        return direct_match

    async for vehicle in db.vehicles.find({"plate_number": {"$exists": True}}):
        if normalize_plate(str(vehicle.get("plate_number", ""))) == normalized_plate:
            return vehicle
    return None


async def create_walk_in_binding(
    *,
    db: AsyncIOMotorDatabase,
    card_uid: str,
    normalized_plate: str,
) -> Dict[str, Any]:
    existing_vehicle = await find_vehicle_by_normalized_plate(db, normalized_plate)
    if existing_vehicle:
        return {
            "success": False,
            "reason": "walk_in_plate_already_registered",
            "vehicle": existing_vehicle,
        }

    available_slot = await db.parking_slots.find_one({"status": SlotStatus.AVAILABLE.value})
    if not available_slot:
        return {
            "success": False,
            "reason": "parking_full",
        }

    dt = utcnow()
    customer_id = await generate_id(db, "customers", "C")
    vehicle_id = await generate_id(db, "vehicles", "V")

    customer = {
        "customer_id": customer_id,
        "name": f"Khach vang lai {normalized_plate}",
        "phone": None,
        "email": None,
        "address": None,
        "id_card": None,
        "customer_type": "walk_in",
        "balance": 0.0,
        "created_at": dt,
        "updated_at": dt,
        "is_active": True,
        "notes": f"Auto-created from walk-in card {card_uid}",
    }
    vehicle = {
        "vehicle_id": vehicle_id,
        "customer_id": customer_id,
        "plate_number": normalized_plate,
        "vehicle_type": "motorbike",
        "brand": None,
        "model": None,
        "color": None,
        "created_at": dt,
        "updated_at": dt,
        "is_active": True,
    }
    card = {
        "card_uid": card_uid,
        "customer_id": customer_id,
        "vehicle_id": vehicle_id,
        "status": "active",
        "issued_at": dt,
        "expire_at": None,
        "created_at": dt,
        "notes": f"Walk-in card auto-created from OCR plate {normalized_plate}",
    }

    try:
        await db.customers.insert_one(customer)
        await db.vehicles.insert_one(vehicle)
        await db.rfid_cards.insert_one(card)
    except DuplicateKeyError as exc:
        await rollback_walk_in_binding(
            db=db,
            card_uid=card_uid,
            customer_id=customer_id,
            vehicle_id=vehicle_id,
        )
        logger.warning("[ACCESS] Walk-in create conflict uid=%s plate=%s error=%s", card_uid, normalized_plate, exc)
        return {
            "success": False,
            "reason": "walk_in_create_conflict",
        }

    logger.info(
        "[ACCESS] Walk-in created uid=%s customer=%s vehicle=%s plate=%s",
        card_uid,
        customer_id,
        vehicle_id,
        normalized_plate,
    )
    return {
        "success": True,
        "customer": customer,
        "vehicle": vehicle,
        "card": card,
    }


async def rollback_walk_in_binding(
    *,
    db: AsyncIOMotorDatabase,
    card_uid: str,
    customer_id: str,
    vehicle_id: str,
) -> None:
    await db.rfid_cards.delete_one(
        {
            "card_uid": card_uid,
            "customer_id": customer_id,
            "vehicle_id": vehicle_id,
            "notes": {"$regex": "^Walk-in card auto-created"},
        }
    )
    await db.vehicles.delete_one(
        {
            "vehicle_id": vehicle_id,
            "customer_id": customer_id,
            "is_active": True,
        }
    )
    await db.customers.delete_one(
        {
            "customer_id": customer_id,
            "customer_type": "walk_in",
            "is_active": True,
        }
    )


async def process_entry(
    *,
    db: AsyncIOMotorDatabase,
    card: Dict[str, Any],
    vehicle: Dict[str, Any],
    gate_id: int,
    capture_batch_id: str,
    ocr_plate: str,
    ocr_confidence: float,
    image_ids: Sequence[str],
    review_required: bool,
    processing_metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    dt = utcnow()
    session_id = await generate_id(db, "sessions", "S")

    slot_started_at = time.perf_counter()
    available_slot = await db.parking_slots.find_one_and_update(
        {"status": SlotStatus.AVAILABLE.value},
        {
            "$set": {
                "status": SlotStatus.OCCUPIED.value,
                "vehicle_id": card["vehicle_id"],
                "session_id": session_id,
                "updated_at": dt,
            }
        },
        sort=[("row", 1), ("col", 1), ("slot_id", 1)],
        return_document=ReturnDocument.AFTER,
    )
    if processing_metrics:
        set_backend_duration(processing_metrics, "slot_reservation_ms", slot_started_at)

    if not available_slot:
        return await reject_event(
            db=db,
            card_uid=card["card_uid"],
            gate_id=gate_id,
            capture_batch_id=capture_batch_id,
            reason="parking_full",
            ocr_plate=ocr_plate,
            ocr_confidence=ocr_confidence,
            expected_plate=normalize_plate(str(vehicle.get("plate_number", ""))),
            customer_id=card.get("customer_id"),
            vehicle_id=card.get("vehicle_id"),
            image_ids=image_ids,
            action="entry",
            processing_metrics=processing_metrics,
        )

    session = {
        "session_id": session_id,
        "card_uid": card["card_uid"],
        "customer_id": card["customer_id"],
        "vehicle_id": card["vehicle_id"],
        "slot_id": available_slot["slot_id"],
        "entry_gate_id": gate_id,
        "exit_gate_id": None,
        "entry_time": dt,
        "exit_time": None,
        "distance_cm": None,
        "status": SessionStatus.IN_PROGRESS.value,
        "parking_fee": 0.0,
        "created_at": dt,
        "entry_capture_batch_id": capture_batch_id,
        "entry_image_ids": list(image_ids),
        "entry_plate_ocr": ocr_plate,
        "entry_ocr_confidence": ocr_confidence,
        "review_required": review_required,
    }
    try:
        session_insert_started_at = time.perf_counter()
        await db.sessions.insert_one(session)
        if processing_metrics:
            set_backend_duration(processing_metrics, "entry_session_insert_ms", session_insert_started_at)
    except Exception:
        logger.exception("[ACCESS] Failed to create entry session; releasing reserved slot")
        await db.parking_slots.update_one(
            {"slot_id": available_slot["slot_id"], "session_id": session_id},
            {
                "$set": {
                    "status": SlotStatus.AVAILABLE.value,
                    "vehicle_id": None,
                    "session_id": None,
                    "updated_at": utcnow(),
                }
            },
        )
        raise

    if processing_metrics:
        mark_backend_timestamp(processing_metrics, "gate_publish_started_at")
    gate_publish_started_at = time.perf_counter()
    gate_open_sent = await publish_open_gate()
    if processing_metrics:
        set_backend_duration(processing_metrics, "gate_publish_ms", gate_publish_started_at)
        mark_backend_timestamp(processing_metrics, "gate_publish_finished_at")
    event_id = await generate_id(db, "parking_events", "E")
    if not gate_open_sent:
        logger.error(
            "[ACCESS] Entry gate publish failed; rolling back session=%s slot=%s",
            session_id,
            available_slot["slot_id"],
        )
        await db.sessions.delete_one({"session_id": session_id, "status": SessionStatus.IN_PROGRESS.value})
        await db.parking_slots.update_one(
            {"slot_id": available_slot["slot_id"], "session_id": session_id},
            {
                "$set": {
                    "status": SlotStatus.AVAILABLE.value,
                    "vehicle_id": None,
                    "session_id": None,
                    "updated_at": utcnow(),
                }
            },
        )

        if processing_metrics:
            mark_backend_timestamp(processing_metrics, "decision_finished_at")
        event_doc = build_event_doc(
            event_id=event_id,
            card_uid=card["card_uid"],
            gate_id=gate_id,
            capture_batch_id=capture_batch_id,
            action="entry",
            decision="rejected",
            reason="gate_publish_failed",
            ocr_plate=ocr_plate,
            ocr_confidence=ocr_confidence,
            expected_plate=normalize_plate(str(vehicle.get("plate_number", ""))),
            session_id=session_id,
            customer_id=card["customer_id"],
            vehicle_id=card["vehicle_id"],
            image_ids=image_ids,
            gate_open_sent=False,
            review_required=True,
            processing_metrics=processing_metrics,
        )
        event_doc["rolled_back"] = True
        event_doc["slot_id"] = available_slot["slot_id"]
        await record_parking_event(db, event_doc)
        await link_captures_to_decision(
            db=db,
            capture_batch_id=capture_batch_id,
            session_id=session_id,
            event_id=event_id,
            event_type="entry",
            decision="rejected",
            reason="gate_publish_failed",
        )
        await publish_parking_status_update(db)
        return {
            "success": False,
            "decision": "rejected",
            "action": "entry",
            "reason": "gate_publish_failed",
            "open_gate": False,
            "session_id": session_id,
            "slot_id": available_slot["slot_id"],
            "rolled_back": True,
            "event": serialize_mongodb_document(event_doc),
        }

    if processing_metrics:
        mark_backend_timestamp(processing_metrics, "decision_finished_at")
    event_doc = build_event_doc(
        event_id=event_id,
        card_uid=card["card_uid"],
        gate_id=gate_id,
        capture_batch_id=capture_batch_id,
        action="entry",
        decision="accepted",
        reason=None,
        ocr_plate=ocr_plate,
        ocr_confidence=ocr_confidence,
        expected_plate=normalize_plate(str(vehicle.get("plate_number", ""))),
        session_id=session_id,
        customer_id=card["customer_id"],
        vehicle_id=card["vehicle_id"],
        image_ids=image_ids,
        gate_open_sent=True,
        review_required=review_required,
        processing_metrics=processing_metrics,
    )
    await record_parking_event(db, event_doc)
    await link_captures_to_decision(
        db=db,
        capture_batch_id=capture_batch_id,
        session_id=session_id,
        event_id=event_id,
        event_type="entry",
        decision="accepted",
        reason=event_doc["reason"],
    )
    await publish_parking_status_update(db)

    return {
        "success": True,
        "decision": "accepted",
        "action": "entry",
        "open_gate": gate_open_sent,
        "session_id": session_id,
        "slot_id": available_slot["slot_id"],
        "review_required": review_required,
        "event": serialize_mongodb_document(event_doc),
    }


async def process_exit(
    *,
    db: AsyncIOMotorDatabase,
    card: Dict[str, Any],
    vehicle: Dict[str, Any],
    active_session: Dict[str, Any],
    gate_id: int,
    capture_batch_id: str,
    ocr_plate: str,
    ocr_confidence: float,
    image_ids: Sequence[str],
    review_required: bool,
    review_reason: Optional[str],
    processing_metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    dt = utcnow()
    entry_time = active_session["entry_time"]
    package_lookup_started_at = time.perf_counter()
    active_package = await db.packages.find_one(
        {
            "customer_id": card["customer_id"],
            "status": "active",
            "expire_date": {"$gt": dt},
        }
    )
    if processing_metrics:
        set_backend_duration(processing_metrics, "package_lookup_ms", package_lookup_started_at)
    parking_fee = 0.0 if active_package else FeeCalculator.calculate_parking_fee(entry_time, dt)

    if processing_metrics:
        mark_backend_timestamp(processing_metrics, "gate_publish_started_at")
    gate_publish_started_at = time.perf_counter()
    gate_open_sent = await publish_open_gate()
    if processing_metrics:
        set_backend_duration(processing_metrics, "gate_publish_ms", gate_publish_started_at)
        mark_backend_timestamp(processing_metrics, "gate_publish_finished_at")
    event_id = await generate_id(db, "parking_events", "E")
    if not gate_open_sent:
        if processing_metrics:
            mark_backend_timestamp(processing_metrics, "decision_finished_at")
        event_doc = build_event_doc(
            event_id=event_id,
            card_uid=card["card_uid"],
            gate_id=gate_id,
            capture_batch_id=capture_batch_id,
            action="exit",
            decision="rejected",
            reason="gate_publish_failed",
            ocr_plate=ocr_plate,
            ocr_confidence=ocr_confidence,
            expected_plate=normalize_plate(str(vehicle.get("plate_number", ""))),
            session_id=active_session["session_id"],
            customer_id=card["customer_id"],
            vehicle_id=card["vehicle_id"],
            image_ids=image_ids,
            gate_open_sent=False,
            review_required=True,
            processing_metrics=processing_metrics,
        )
        event_doc["parking_fee"] = parking_fee
        event_doc["review_reason"] = review_reason or "gate_publish_failed"
        await record_parking_event(db, event_doc)
        await link_captures_to_decision(
            db=db,
            capture_batch_id=capture_batch_id,
            session_id=active_session["session_id"],
            event_id=event_id,
            event_type="exit",
            decision="rejected",
            reason="gate_publish_failed",
        )
        return {
            "success": False,
            "decision": "rejected",
            "action": "exit",
            "reason": "gate_publish_failed",
            "open_gate": False,
            "session_id": active_session["session_id"],
            "parking_fee": parking_fee,
            "event": serialize_mongodb_document(event_doc),
        }

    session_update_started_at = time.perf_counter()
    await db.sessions.update_one(
        {"session_id": active_session["session_id"]},
        {
            "$set": {
                "exit_time": dt,
                "exit_gate_id": gate_id,
                "status": SessionStatus.COMPLETED.value,
                "parking_fee": parking_fee,
                "exit_capture_batch_id": capture_batch_id,
                "exit_image_ids": list(image_ids),
                "exit_plate_ocr": ocr_plate,
                "exit_ocr_confidence": ocr_confidence,
                "exit_review_required": review_required,
                "exit_review_reason": review_reason,
            }
        },
    )
    if processing_metrics:
        set_backend_duration(processing_metrics, "exit_session_update_ms", session_update_started_at)

    if active_session.get("slot_id"):
        slot_release_started_at = time.perf_counter()
        await db.parking_slots.update_one(
            {"slot_id": active_session["slot_id"]},
            {
                "$set": {
                    "status": SlotStatus.AVAILABLE.value,
                    "vehicle_id": None,
                    "session_id": None,
                    "updated_at": dt,
                }
            },
        )
        if processing_metrics:
            set_backend_duration(processing_metrics, "slot_release_ms", slot_release_started_at)

    transaction_id = None
    if parking_fee > 0:
        transaction_id = await generate_id(db, "transactions", "T")
        transaction_insert_started_at = time.perf_counter()
        await db.transactions.insert_one(
            {
                "transaction_id": transaction_id,
                "customer_id": card["customer_id"],
                "transaction_type": "parking_fee",
                "amount": parking_fee,
                "session_id": active_session["session_id"],
                "payment_method": "cash",
                "description": f"Parking fee - {active_session['session_id']}",
                "created_at": dt,
            }
        )
        if processing_metrics:
            set_backend_duration(processing_metrics, "transaction_insert_ms", transaction_insert_started_at)

    if processing_metrics:
        mark_backend_timestamp(processing_metrics, "decision_finished_at")
    event_doc = build_event_doc(
        event_id=event_id,
        card_uid=card["card_uid"],
        gate_id=gate_id,
        capture_batch_id=capture_batch_id,
        action="exit",
        decision="accepted",
        reason=None,
        ocr_plate=ocr_plate,
        ocr_confidence=ocr_confidence,
        expected_plate=normalize_plate(str(vehicle.get("plate_number", ""))),
        session_id=active_session["session_id"],
        customer_id=card["customer_id"],
        vehicle_id=card["vehicle_id"],
        image_ids=image_ids,
        gate_open_sent=True,
        review_required=review_required,
        processing_metrics=processing_metrics,
    )
    event_doc["parking_fee"] = parking_fee
    event_doc["transaction_id"] = transaction_id
    event_doc["review_reason"] = review_reason
    await record_parking_event(db, event_doc)
    await link_captures_to_decision(
        db=db,
        capture_batch_id=capture_batch_id,
        session_id=active_session["session_id"],
        event_id=event_id,
        event_type="exit",
        decision="accepted",
        reason=event_doc["reason"],
    )
    await publish_parking_status_update(db)

    return {
        "success": True,
        "decision": "accepted",
        "action": "exit",
        "open_gate": True,
        "session_id": active_session["session_id"],
        "parking_fee": parking_fee,
        "transaction_id": transaction_id,
        "review_required": review_required,
        "event": serialize_mongodb_document(event_doc),
    }


@router.post("/rfid-camera")
async def handle_rfid_camera_event(
    request: Request,
    card_uid: str = Form(...),
    gate_id: int = Form(1),
    gate_direction: str = Form("auto"),
    capture_batch_id: str = Form(...),
    ocr_plate: str = Form(""),
    ocr_confidence: float = Form(0.0),
    frame_metadata: str = Form("[]"),
    processing_metrics: str = Form("{}"),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    request_started_at = time.perf_counter()
    processing_metrics_doc = init_processing_metrics(parse_processing_metrics(processing_metrics))
    card_uid = card_uid.strip()
    if not card_uid:
        raise HTTPException(status_code=400, detail="card_uid is required")

    capture_batch_id = capture_batch_id.strip()
    if not capture_batch_id:
        raise HTTPException(status_code=400, detail="capture_batch_id is required")

    gate_direction = normalize_gate_direction(gate_direction)
    set_backend_duration(processing_metrics_doc, "request_validation_ms", request_started_at)

    existing_event = await db.parking_events.find_one({"capture_batch_id": capture_batch_id})
    if existing_event:
        serialized_event = serialize_mongodb_document(existing_event)
        return {
            "success": existing_event.get("decision") == "accepted",
            "decision": existing_event.get("decision"),
            "action": existing_event.get("event_type"),
            "reason": existing_event.get("reason"),
            "open_gate": bool(existing_event.get("gate_open_sent", False)),
            "session_id": existing_event.get("session_id"),
            "idempotent": True,
            "event": serialized_event,
        }

    normalized_ocr_plate = normalize_plate(ocr_plate)
    ocr_valid = is_valid_plate(normalized_ocr_plate)
    parsed_frame_metadata = parse_frame_metadata(frame_metadata)
    multipart_parse_started_at = time.perf_counter()
    multipart_form = await request.form()
    set_backend_duration(processing_metrics_doc, "multipart_parse_ms", multipart_parse_started_at)
    uploaded_images = normalize_uploaded_images(multipart_form.getlist("images"))
    logger.info(
        "[ACCESS] RFID camera event batch=%s uid=%s images=%s",
        capture_batch_id,
        card_uid,
        len(uploaded_images),
    )

    image_store_started_at = time.perf_counter()
    mark_backend_timestamp(processing_metrics_doc, "image_store_started_at")
    stored_images = await store_uploaded_images(
        db=db,
        card_uid=card_uid,
        gate_id=gate_id,
        capture_batch_id=capture_batch_id,
        ocr_plate=normalized_ocr_plate,
        ocr_confidence=ocr_confidence,
        frame_metadata=parsed_frame_metadata,
        images=uploaded_images,
    )
    set_backend_duration(processing_metrics_doc, "image_store_ms", image_store_started_at)
    mark_backend_timestamp(processing_metrics_doc, "image_store_finished_at")
    image_ids = [str(item["gridfs_file_id"]) for item in stored_images]

    lookup_started_at = time.perf_counter()
    mark_backend_timestamp(processing_metrics_doc, "db_lookup_started_at")
    if REGISTRATION_MODE["enabled"]:
        await db.pending_scans.insert_one(
            {
                "card_uid": card_uid,
                "gate_id": gate_id,
                "distance_cm": None,
                "scanned_at": utcnow(),
                "source": "rfid_camera",
            }
        )
        set_backend_duration(processing_metrics_doc, "db_lookup_ms", lookup_started_at)
        mark_backend_timestamp(processing_metrics_doc, "db_lookup_finished_at")
        return await reject_event(
            db=db,
            card_uid=card_uid,
            gate_id=gate_id,
            capture_batch_id=capture_batch_id,
            reason="registration_mode_active",
            ocr_plate=normalized_ocr_plate,
            ocr_confidence=ocr_confidence,
            expected_plate=None,
            customer_id=None,
            vehicle_id=None,
            image_ids=image_ids,
            action=None,
            processing_metrics=processing_metrics_doc,
        )

    card = await db.rfid_cards.find_one({"card_uid": card_uid})
    if card and card.get("status") != "active":
        set_backend_duration(processing_metrics_doc, "db_lookup_ms", lookup_started_at)
        mark_backend_timestamp(processing_metrics_doc, "db_lookup_finished_at")
        return await reject_event(
            db=db,
            card_uid=card_uid,
            gate_id=gate_id,
            capture_batch_id=capture_batch_id,
            reason="rfid_card_not_found_or_inactive",
            ocr_plate=normalized_ocr_plate,
            ocr_confidence=ocr_confidence,
            expected_plate=None,
            customer_id=card.get("customer_id"),
            vehicle_id=card.get("vehicle_id"),
            image_ids=image_ids,
            processing_metrics=processing_metrics_doc,
        )

    walk_in_created = False
    if not card:
        if gate_direction == "exit":
            set_backend_duration(processing_metrics_doc, "db_lookup_ms", lookup_started_at)
            mark_backend_timestamp(processing_metrics_doc, "db_lookup_finished_at")
            return await reject_event(
                db=db,
                card_uid=card_uid,
                gate_id=gate_id,
                capture_batch_id=capture_batch_id,
                reason="walk_in_exit_card_not_registered",
                ocr_plate=normalized_ocr_plate,
                ocr_confidence=ocr_confidence,
                expected_plate=None,
                customer_id=None,
                vehicle_id=None,
                image_ids=image_ids,
                action="exit",
                processing_metrics=processing_metrics_doc,
            )

        if not ocr_valid:
            set_backend_duration(processing_metrics_doc, "db_lookup_ms", lookup_started_at)
            mark_backend_timestamp(processing_metrics_doc, "db_lookup_finished_at")
            return await reject_event(
                db=db,
                card_uid=card_uid,
                gate_id=gate_id,
                capture_batch_id=capture_batch_id,
                reason="walk_in_ocr_failed",
                ocr_plate=normalized_ocr_plate,
                ocr_confidence=ocr_confidence,
                expected_plate=None,
                customer_id=None,
                vehicle_id=None,
                image_ids=image_ids,
                action="entry",
                processing_metrics=processing_metrics_doc,
            )

        walk_in = await create_walk_in_binding(
            db=db,
            card_uid=card_uid,
            normalized_plate=normalized_ocr_plate,
        )
        if not walk_in.get("success"):
            existing_vehicle = walk_in.get("vehicle") or {}
            set_backend_duration(processing_metrics_doc, "db_lookup_ms", lookup_started_at)
            mark_backend_timestamp(processing_metrics_doc, "db_lookup_finished_at")
            return await reject_event(
                db=db,
                card_uid=card_uid,
                gate_id=gate_id,
                capture_batch_id=capture_batch_id,
                reason=str(walk_in.get("reason") or "walk_in_create_failed"),
                ocr_plate=normalized_ocr_plate,
                ocr_confidence=ocr_confidence,
                expected_plate=normalize_plate(str(existing_vehicle.get("plate_number", ""))) or None,
                customer_id=existing_vehicle.get("customer_id"),
                vehicle_id=existing_vehicle.get("vehicle_id"),
                image_ids=image_ids,
                action="entry",
                processing_metrics=processing_metrics_doc,
            )

        card = walk_in["card"]
        vehicle = walk_in["vehicle"]
        walk_in_created = True
    else:
        vehicle = await db.vehicles.find_one({"vehicle_id": card.get("vehicle_id"), "is_active": True})

    if not vehicle:
        set_backend_duration(processing_metrics_doc, "db_lookup_ms", lookup_started_at)
        mark_backend_timestamp(processing_metrics_doc, "db_lookup_finished_at")
        return await reject_event(
            db=db,
            card_uid=card_uid,
            gate_id=gate_id,
            capture_batch_id=capture_batch_id,
            reason="vehicle_not_found_or_inactive",
            ocr_plate=normalized_ocr_plate,
            ocr_confidence=ocr_confidence,
            expected_plate=None,
            customer_id=card.get("customer_id"),
            vehicle_id=card.get("vehicle_id"),
            image_ids=image_ids,
            processing_metrics=processing_metrics_doc,
        )

    expected_plate = normalize_plate(str(vehicle.get("plate_number", "")))
    active_session = await db.sessions.find_one(
        {"card_uid": card_uid, "status": SessionStatus.IN_PROGRESS.value}
    )
    set_backend_duration(processing_metrics_doc, "db_lookup_ms", lookup_started_at)
    mark_backend_timestamp(processing_metrics_doc, "db_lookup_finished_at")
    mark_backend_timestamp(processing_metrics_doc, "decision_started_at")

    if gate_direction == "entry":
        action = "entry"
        if active_session:
            return await reject_event(
                db=db,
                card_uid=card_uid,
                gate_id=gate_id,
                capture_batch_id=capture_batch_id,
                reason="entry_session_already_active",
                ocr_plate=normalized_ocr_plate,
                ocr_confidence=ocr_confidence,
                expected_plate=expected_plate,
                customer_id=card.get("customer_id"),
                vehicle_id=card.get("vehicle_id"),
                image_ids=image_ids,
                action=action,
                processing_metrics=processing_metrics_doc,
            )
    elif gate_direction == "exit":
        action = "exit"
        if not active_session:
            return await reject_event(
                db=db,
                card_uid=card_uid,
                gate_id=gate_id,
                capture_batch_id=capture_batch_id,
                reason="exit_session_not_found",
                ocr_plate=normalized_ocr_plate,
                ocr_confidence=ocr_confidence,
                expected_plate=expected_plate,
                customer_id=card.get("customer_id"),
                vehicle_id=card.get("vehicle_id"),
                image_ids=image_ids,
                action=action,
                processing_metrics=processing_metrics_doc,
            )
    else:
        action = "exit" if active_session else "entry"

    if action == "entry":
        review_required = False
        if not ocr_valid:
            if STRICT_OCR_BEFORE_GATE or OCR_ENTRY_POLICY == "required":
                return await reject_event(
                    db=db,
                    card_uid=card_uid,
                    gate_id=gate_id,
                    capture_batch_id=capture_batch_id,
                    reason="entry_ocr_failed",
                    ocr_plate=normalized_ocr_plate,
                    ocr_confidence=ocr_confidence,
                    expected_plate=expected_plate,
                    customer_id=card.get("customer_id"),
                    vehicle_id=card.get("vehicle_id"),
                    image_ids=image_ids,
                    action=action,
                    processing_metrics=processing_metrics_doc,
                )
            review_required = True
        elif normalized_ocr_plate != expected_plate:
            if not ALLOW_ENTRY_ON_OCR_MISMATCH:
                return await reject_event(
                    db=db,
                    card_uid=card_uid,
                    gate_id=gate_id,
                    capture_batch_id=capture_batch_id,
                    reason="entry_plate_mismatch",
                    ocr_plate=normalized_ocr_plate,
                    ocr_confidence=ocr_confidence,
                    expected_plate=expected_plate,
                    customer_id=card.get("customer_id"),
                    vehicle_id=card.get("vehicle_id"),
                    image_ids=image_ids,
                    action=action,
                    processing_metrics=processing_metrics_doc,
                )
            review_required = True

        entry_result = await process_entry(
            db=db,
            card=card,
            vehicle=vehicle,
            gate_id=gate_id,
            capture_batch_id=capture_batch_id,
            ocr_plate=normalized_ocr_plate,
            ocr_confidence=ocr_confidence,
            image_ids=image_ids,
            review_required=review_required,
            processing_metrics=processing_metrics_doc,
        )
        if walk_in_created:
            if entry_result.get("decision") == "accepted":
                entry_result["walk_in_created"] = True
                entry_result["customer_type"] = "walk_in"
                entry_result["customer_id"] = card.get("customer_id")
                entry_result["vehicle_id"] = card.get("vehicle_id")
            else:
                await rollback_walk_in_binding(
                    db=db,
                    card_uid=card["card_uid"],
                    customer_id=card["customer_id"],
                    vehicle_id=card["vehicle_id"],
                )
                entry_result["walk_in_created"] = False
                entry_result["walk_in_rolled_back"] = True
        return entry_result

    exit_review_required = False
    exit_review_reason = None

    if not ocr_valid:
        if STRICT_OCR_BEFORE_GATE or (OCR_EXIT_POLICY == "required" and not ALLOW_EXIT_ON_OCR_FAILED):
            return await reject_event(
                db=db,
                card_uid=card_uid,
                gate_id=gate_id,
                capture_batch_id=capture_batch_id,
                reason="exit_ocr_failed",
                ocr_plate=normalized_ocr_plate,
                ocr_confidence=ocr_confidence,
                expected_plate=expected_plate,
                customer_id=card.get("customer_id"),
                vehicle_id=card.get("vehicle_id"),
                image_ids=image_ids,
                action=action,
                processing_metrics=processing_metrics_doc,
            )
        exit_review_required = True
        exit_review_reason = "exit_ocr_failed_allowed"
    elif normalized_ocr_plate != expected_plate:
        if ALLOW_EXIT_ON_OCR_FUZZY_MATCH and is_fuzzy_plate_match(normalized_ocr_plate, expected_plate):
            exit_review_required = True
            exit_review_reason = "exit_plate_fuzzy_match"
        elif not ALLOW_EXIT_ON_OCR_MISMATCH:
            return await reject_event(
                db=db,
                card_uid=card_uid,
                gate_id=gate_id,
                capture_batch_id=capture_batch_id,
                reason="exit_plate_mismatch",
                ocr_plate=normalized_ocr_plate,
                ocr_confidence=ocr_confidence,
                expected_plate=expected_plate,
                customer_id=card.get("customer_id"),
                vehicle_id=card.get("vehicle_id"),
                image_ids=image_ids,
                action=action,
                processing_metrics=processing_metrics_doc,
            )
        else:
            exit_review_required = True
            exit_review_reason = "exit_plate_mismatch_allowed"

    return await process_exit(
        db=db,
        card=card,
        vehicle=vehicle,
        active_session=active_session,
        gate_id=gate_id,
        capture_batch_id=capture_batch_id,
        ocr_plate=normalized_ocr_plate,
        ocr_confidence=ocr_confidence,
        image_ids=image_ids,
        review_required=exit_review_required,
        review_reason=exit_review_reason,
        processing_metrics=processing_metrics_doc,
    )


@router.get("/captures")
async def list_recent_captures(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    docs = await (
        db[CAPTURE_METADATA_COLLECTION]
        .find({})
        .sort("captured_at", -1)
        .limit(limit)
        .to_list(length=limit)
    )

    captures = []
    for doc in docs:
        serialized = serialize_mongodb_document(doc)
        file_id = serialized.get("gridfs_file_id")
        if file_id and not serialized.get("view_url"):
            serialized["view_url"] = f"/api/v1/access-events/images/{file_id}"
        captures.append(serialized)

    return {
        "success": True,
        "total": len(captures),
        "captures": captures,
    }


@router.get("/events")
async def list_recent_access_events(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    docs = await (
        db.parking_events
        .find({})
        .sort("created_at", -1)
        .limit(limit)
        .to_list(length=limit)
    )
    events = [serialize_mongodb_document(doc) for doc in docs]
    batch_ids = [event.get("capture_batch_id") for event in events if event.get("capture_batch_id")]

    captures_by_batch: Dict[str, List[Dict[str, Any]]] = {}
    if batch_ids:
        capture_docs = await (
            db[CAPTURE_METADATA_COLLECTION]
            .find({"capture_batch_id": {"$in": batch_ids}})
            .sort("frame_no", 1)
            .to_list(length=max(len(batch_ids) * 3, 1))
        )
        for capture_doc in capture_docs:
            serialized_capture = serialize_mongodb_document(capture_doc)
            file_id = serialized_capture.get("gridfs_file_id")
            if file_id and not serialized_capture.get("view_url"):
                serialized_capture["view_url"] = f"/api/v1/access-events/images/{file_id}"
            batch_id = serialized_capture.get("capture_batch_id")
            if batch_id:
                captures_by_batch.setdefault(batch_id, []).append(serialized_capture)

    for event in events:
        batch_id = event.get("capture_batch_id")
        batch_captures = captures_by_batch.get(batch_id, [])
        event["capture_images"] = batch_captures
        if not event.get("image_ids") and batch_captures:
            event["image_ids"] = [
                str(capture.get("gridfs_file_id"))
                for capture in batch_captures
                if capture.get("gridfs_file_id")
            ]

    return {
        "success": True,
        "total": len(events),
        "events": events,
    }


@router.get("/debug/images/{file_id}/quality")
async def get_camera_image_quality(file_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    content, grid_out = await read_gridfs_image_content(db, file_id)
    metadata = grid_out.metadata or {}
    image = rotate_debug_image(decode_image_bytes(content))
    return {
        "success": True,
        "file_id": file_id,
        "filename": grid_out.filename,
        "metadata": serialize_mongodb_document(metadata),
        "quality": calculate_image_quality(image, metadata),
        "roi": {
            "x1": PLATE_ROI_X1,
            "y1": PLATE_ROI_Y1,
            "x2": PLATE_ROI_X2,
            "y2": PLATE_ROI_Y2,
            "rotation": OCR_DEBUG_ROTATION,
            "selected_plate_bbox": metadata.get("selected_plate_bbox"),
        },
    }


@router.get("/debug/images/{file_id}/roi")
async def get_camera_image_roi(file_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    content, grid_out = await read_gridfs_image_content(db, file_id)
    metadata = grid_out.metadata or {}
    image = rotate_debug_image(decode_image_bytes(content))
    roi = crop_detected_plate(image, metadata)
    quality = calculate_image_quality(image, metadata)
    headers = {
        "Cache-Control": "no-store",
        "X-Blur-Score": str(quality["blur_score"]),
        "X-ROI": f"detected={metadata.get('selected_plate_bbox')};rotation={OCR_DEBUG_ROTATION}",
    }
    return encode_image_response(roi, extension=".jpg", media_type="image/jpeg", headers=headers)


@router.get("/debug/images/{file_id}/preprocess")
async def get_camera_image_preprocess(file_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    content, grid_out = await read_gridfs_image_content(db, file_id)
    metadata = grid_out.metadata or {}
    image = rotate_debug_image(decode_image_bytes(content))
    processed = preprocess_debug_image(image, metadata)
    quality = calculate_image_quality(image, metadata)
    headers = {
        "Cache-Control": "no-store",
        "X-Blur-Score": str(quality["blur_score"]),
        "X-ROI": f"detected={metadata.get('selected_plate_bbox')};rotation={OCR_DEBUG_ROTATION}",
    }
    return encode_image_response(processed, extension=".png", media_type="image/png", headers=headers)


@router.post("/dev/reset-active-session/{card_uid}")
async def dev_reset_active_session(
    card_uid: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    if not ENABLE_DEV_ACCESS_TOOLS:
        raise HTTPException(status_code=404, detail="Not found")

    card_uid = card_uid.strip()
    session = await db.sessions.find_one(
        {"card_uid": card_uid, "status": SessionStatus.IN_PROGRESS.value}
    )
    if not session:
        return {
            "success": True,
            "reset": False,
            "message": "No active session found",
            "card_uid": card_uid,
        }

    now = utcnow()
    await db.sessions.update_one(
        {"_id": session["_id"]},
        {
            "$set": {
                "status": SessionStatus.CANCELLED.value,
                "exit_time": now,
                "updated_at": now,
                "cancel_reason": "dev_reset_active_session",
            }
        },
    )

    slot_id = session.get("slot_id")
    if slot_id:
        await db.parking_slots.update_one(
            {"slot_id": slot_id, "session_id": session.get("session_id")},
            {
                "$set": {
                    "status": SlotStatus.AVAILABLE.value,
                    "vehicle_id": None,
                    "session_id": None,
                    "updated_at": now,
                }
            },
        )
    await publish_parking_status_update(db)

    return {
        "success": True,
        "reset": True,
        "card_uid": card_uid,
        "session_id": session.get("session_id"),
        "slot_id": slot_id,
        "status": SessionStatus.CANCELLED.value,
    }


@router.post("/dev/cleanup-active-sessions")
async def dev_cleanup_active_sessions(
    older_than_days: int = Query(7, ge=1, le=3650),
    dry_run: bool = Query(True),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    if not ENABLE_DEV_ACCESS_TOOLS:
        raise HTTPException(status_code=404, detail="Not found")

    from datetime import timedelta

    now = utcnow()
    cutoff = now - timedelta(days=older_than_days)
    sessions = await (
        db.sessions
        .find({"status": SessionStatus.IN_PROGRESS.value, "entry_time": {"$lt": cutoff}})
        .sort("entry_time", 1)
        .to_list(length=200)
    )

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "older_than_days": older_than_days,
            "cutoff": cutoff.isoformat(),
            "total": len(sessions),
            "sessions": [serialize_mongodb_document(session) for session in sessions],
        }

    reset_items = []
    for session in sessions:
        await db.sessions.update_one(
            {"_id": session["_id"]},
            {
                "$set": {
                    "status": SessionStatus.CANCELLED.value,
                    "exit_time": now,
                    "updated_at": now,
                    "cancel_reason": "dev_cleanup_active_sessions",
                }
            },
        )

        slot_id = session.get("slot_id")
        if slot_id:
            await db.parking_slots.update_one(
                {"slot_id": slot_id, "session_id": session.get("session_id")},
                {
                    "$set": {
                        "status": SlotStatus.AVAILABLE.value,
                        "vehicle_id": None,
                        "session_id": None,
                        "updated_at": now,
                    }
                },
            )

        reset_items.append(
            {
                "session_id": session.get("session_id"),
                "card_uid": session.get("card_uid"),
                "slot_id": slot_id,
            }
        )

    await publish_parking_status_update(db)

    return {
        "success": True,
        "dry_run": False,
        "older_than_days": older_than_days,
        "cutoff": cutoff.isoformat(),
        "reset_total": len(reset_items),
        "reset_sessions": reset_items,
    }


@router.get("/images/{file_id}")
async def get_camera_image(file_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    content, grid_out = await read_gridfs_image_content(db, file_id)
    content_type = grid_out.metadata.get("content_type", "image/jpeg") if grid_out.metadata else "image/jpeg"
    return Response(content=content, media_type=content_type, headers={"Cache-Control": "no-store"})
