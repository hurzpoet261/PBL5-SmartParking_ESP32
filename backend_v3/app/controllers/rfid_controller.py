"""
RFID controller.

The production gate flow is:
RFID -> OCR bridge -> POST /scan-with-ocr -> backend decision -> gate command.

POST /scan is retained only for legacy registration visibility. It never opens
the gate because it does not provide OCR evidence.
"""
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from pymongo import ReturnDocument

from app.database import get_database
from app.models.parking_slot import SlotStatus
from app.models.session import SessionStatus
from app.services.fee_calculator import FeeCalculator
from app.utils.id_generator import generate_id
from app.utils.serializers import serialize_mongodb_document

logger = logging.getLogger(__name__)
DEVICE_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")

router = APIRouter()

REGISTRATION_MODE = {
    "enabled": False,
    "started_at": None,
}


class RFIDScanRequest(BaseModel):
    """Legacy RFID scan request without OCR evidence."""

    card_uid: str = Field(..., min_length=1, description="Card UID")
    gate_id: int = Field(1, ge=1, description="Gate ID")
    device_id: Optional[str] = Field(None, description="ESP32 gate device ID")
    distance_cm: Optional[float] = Field(None, description="Distance from ultrasonic sensor")
    timestamp: Optional[float] = Field(
        None,
        description="Device timestamp. Server time remains authoritative.",
    )


class RFIDScanWithOCRRequest(RFIDScanRequest):
    """Authoritative gate scan request produced by the OCR bridge."""

    device_id: str = Field(..., min_length=1, description="ESP32 gate device ID")
    ocr_plate: str = Field(..., min_length=1, description="License plate extracted by OCR")
    ocr_confidence: Optional[float] = Field(None, ge=0, le=1)
    capture_batch_id: Optional[str] = None


def normalize_plate(value: str) -> str:
    """Normalize OCR and stored plate formats before comparing them."""

    return re.sub(r"[^0-9A-Z]", "", (value or "").upper())


def deny(reason: str, reason_code: str, **extra: Any) -> Dict[str, Any]:
    """Return a handled access denial without a gate command."""

    return {
        "success": True,
        "allowed": False,
        "action": "deny",
        "reason": reason,
        "reason_code": reason_code,
        "gate_command": None,
        **extra,
    }


def allow(
    action: str,
    reason: str,
    *,
    gate_id: int,
    device_id: str,
    **extra: Any,
) -> Dict[str, Any]:
    """Return an approved backend decision and its targeted gate command."""

    return {
        "success": True,
        "allowed": True,
        "action": action,
        "reason": reason,
        "gate_command": {
            "command": "OPEN",
            "gate_id": gate_id,
            "device_id": device_id,
        },
        **extra,
    }


async def save_pending_scan(
    db: AsyncIOMotorDatabase,
    request: RFIDScanRequest,
    scanned_at: datetime,
) -> None:
    await db.pending_scans.insert_one(
        {
            "card_uid": request.card_uid.strip(),
            "gate_id": request.gate_id,
            "device_id": request.device_id,
            "distance_cm": request.distance_cm,
            "scanned_at": scanned_at,
        }
    )


@router.post("/registration-mode/start")
async def start_registration_mode(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Enable registration mode so new scans are reserved for web registration."""

    REGISTRATION_MODE["enabled"] = True
    REGISTRATION_MODE["started_at"] = datetime.now().isoformat()
    await db.pending_scans.delete_many({})
    return {
        "success": True,
        "message": "Registration mode enabled",
        "started_at": REGISTRATION_MODE["started_at"],
    }


@router.post("/registration-mode/stop")
async def stop_registration_mode():
    """Disable registration mode."""

    REGISTRATION_MODE["enabled"] = False
    REGISTRATION_MODE["started_at"] = None
    return {
        "success": True,
        "message": "Registration mode disabled",
    }


@router.get("/registration-mode")
async def get_registration_mode_status():
    return {
        "success": True,
        "enabled": REGISTRATION_MODE["enabled"],
        "started_at": REGISTRATION_MODE["started_at"],
    }


@router.get("/latest-scan")
async def get_latest_scan(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get the latest scanned card UID for the web registration screen."""

    latest = await db.pending_scans.find_one({}, sort=[("scanned_at", -1)])
    if not latest:
        return {
            "success": False,
            "message": "No RFID card has been scanned yet.",
        }

    return {
        "success": True,
        "card_uid": latest["card_uid"],
        "scanned_at": latest["scanned_at"].isoformat(),
        "gate_id": latest.get("gate_id", 1),
        "device_id": latest.get("device_id"),
    }


@router.delete("/latest-scan")
async def clear_latest_scan(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Clear pending scans after registration."""

    result = await db.pending_scans.delete_many({})
    return {
        "success": True,
        "deleted_count": result.deleted_count,
    }


@router.post("/register-card")
async def register_card(
    card_data: dict,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Register a new RFID card from the existing web form."""

    card_uid = str(card_data.get("card_uid") or "").strip()
    customer_id = str(card_data.get("customer_id") or "").strip()
    vehicle_id = str(card_data.get("vehicle_id") or "").strip()
    status = str(card_data.get("status") or "active").strip()

    if not card_uid or not customer_id or not vehicle_id:
        return {
            "success": False,
            "error": "card_uid, customer_id and vehicle_id are required",
        }

    existing = await db.rfid_cards.find_one({"card_uid": card_uid})
    if existing:
        return {
            "success": False,
            "error": "This RFID card is already registered",
        }

    customer = await db.customers.find_one({"customer_id": customer_id})
    vehicle = await db.vehicles.find_one({"vehicle_id": vehicle_id})
    if not customer or not vehicle or vehicle.get("customer_id") != customer_id:
        return {
            "success": False,
            "error": "Invalid customer and vehicle binding",
        }

    now = datetime.now()
    card_doc = {
        "card_uid": card_uid,
        "customer_id": customer_id,
        "vehicle_id": vehicle_id,
        "status": status,
        "issued_at": now,
        "expire_at": None,
        "created_at": now,
        "notes": "Registered from web",
    }
    await db.rfid_cards.insert_one(card_doc)

    return {
        "success": True,
        "message": "RFID card registered successfully",
        "data": serialize_mongodb_document(card_doc),
    }


@router.post("/scan", deprecated=True)
async def legacy_rfid_scan(
    request: RFIDScanRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Deprecated UID-only endpoint.

    It stores the scan for registration compatibility but cannot authorize gate
    access. Gate authorization requires POST /scan-with-ocr.
    """

    logger.warning("Deprecated UID-only RFID scan received: %s", request.card_uid)
    await save_pending_scan(db, request, datetime.now())
    return deny(
        "OCR evidence is required. Use POST /api/v1/rfid/scan-with-ocr.",
        "OCR_REQUIRED",
        deprecated=True,
        replacement="/api/v1/rfid/scan-with-ocr",
    )


@router.post("/scan-with-ocr")
async def rfid_scan_with_ocr(
    request: RFIDScanWithOCRRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Process the only production gate authorization flow."""

    card_uid = request.card_uid.strip()
    device_id = request.device_id.strip()
    ocr_plate = normalize_plate(request.ocr_plate)
    now = datetime.now()

    logger.info(
        "RFID OCR scan: uid=%s plate=%s gate=%s device=%s",
        card_uid,
        ocr_plate,
        request.gate_id,
        device_id,
    )
    await save_pending_scan(db, request, now)

    if not device_id:
        return deny("Gate device ID is empty.", "DEVICE_ID_EMPTY")

    if not DEVICE_ID_RE.fullmatch(device_id):
        return deny("Gate device ID format is invalid.", "DEVICE_ID_INVALID")

    if not ocr_plate:
        return deny("OCR plate is empty.", "OCR_PLATE_EMPTY")

    card = await db.rfid_cards.find_one({"card_uid": card_uid})
    if not card:
        return deny(
            "RFID card is not registered.",
            "CARD_NOT_REGISTERED",
            card_uid=card_uid,
        )

    if card.get("status") != "active":
        return deny(
            "RFID card is not active.",
            "CARD_NOT_ACTIVE",
            card_status=card.get("status"),
        )

    customer = await db.customers.find_one({"customer_id": card.get("customer_id")})
    vehicle = await db.vehicles.find_one({"vehicle_id": card.get("vehicle_id")})
    if not customer or not vehicle:
        return deny(
            "RFID card binding is incomplete.",
            "INCONSISTENT_CARD_BINDING",
        )

    if not customer.get("is_active", True) or not vehicle.get("is_active", True):
        return deny(
            "Customer or vehicle is inactive.",
            "CUSTOMER_OR_VEHICLE_INACTIVE",
        )

    if vehicle.get("customer_id") != customer.get("customer_id"):
        return deny(
            "Vehicle does not belong to the RFID card customer.",
            "VEHICLE_OWNER_MISMATCH",
        )

    stored_plate = normalize_plate(str(vehicle.get("plate_number") or ""))
    if stored_plate != ocr_plate:
        return deny(
            "OCR plate does not match the RFID vehicle.",
            "OCR_PLATE_MISMATCH",
            stored_plate=stored_plate,
            ocr_plate=ocr_plate,
        )

    active_session = await db.sessions.find_one(
        {
            "card_uid": card_uid,
            "status": SessionStatus.IN_PROGRESS.value,
        }
    )

    if active_session:
        return await checkout_vehicle(
            db,
            request=request,
            card=card,
            customer=customer,
            vehicle=vehicle,
            active_session=active_session,
            now=now,
        )

    return await checkin_vehicle(
        db,
        request=request,
        card=card,
        customer=customer,
        vehicle=vehicle,
        now=now,
    )


async def checkout_vehicle(
    db: AsyncIOMotorDatabase,
    *,
    request: RFIDScanWithOCRRequest,
    card: Dict[str, Any],
    customer: Dict[str, Any],
    vehicle: Dict[str, Any],
    active_session: Dict[str, Any],
    now: datetime,
) -> Dict[str, Any]:
    """Complete an active session and release its slot."""

    active_package = await db.packages.find_one(
        {
            "customer_id": card["customer_id"],
            "vehicle_id": card["vehicle_id"],
            "package_type": {"$in": ["daily", "monthly"]},
            "status": "active",
            "expire_date": {"$gt": now},
        }
    )
    package_type = active_package.get("package_type") if active_package else None
    parking_fee = FeeCalculator.calculate_parking_fee(
        active_session["entry_time"],
        now,
        package_type,
    )

    completed_session = await db.sessions.find_one_and_update(
        {
            "session_id": active_session["session_id"],
            "status": SessionStatus.IN_PROGRESS.value,
        },
        {
            "$set": {
                "exit_time": now,
                "exit_gate_id": request.gate_id,
                "status": SessionStatus.COMPLETED.value,
                "parking_fee": parking_fee,
            }
        },
        return_document=ReturnDocument.BEFORE,
    )
    if not completed_session:
        return deny(
            "Parking session was already completed by another scan.",
            "SESSION_ALREADY_COMPLETED",
        )

    slot_id = completed_session.get("slot_id")
    if slot_id:
        await db.parking_slots.update_one(
            {
                "slot_id": slot_id,
                "session_id": completed_session["session_id"],
            },
            {
                "$set": {
                    "status": SlotStatus.AVAILABLE.value,
                    "vehicle_id": None,
                    "session_id": None,
                    "updated_at": now,
                }
            },
        )

    if parking_fee > 0:
        transaction_id = await generate_id(db, "transactions", "T")
        await db.transactions.insert_one(
            {
                "transaction_id": transaction_id,
                "customer_id": card["customer_id"],
                "transaction_type": "parking_fee",
                "amount": parking_fee,
                "session_id": completed_session["session_id"],
                "payment_method": "cash",
                "description": f"Parking fee - {completed_session['session_id']}",
                "created_at": now,
            }
        )

    duration_minutes = round(
        (now - completed_session["entry_time"]).total_seconds() / 60
    )
    return allow(
        "checkout",
        "Vehicle checked out successfully.",
        gate_id=request.gate_id,
        device_id=request.device_id.strip(),
        customer_name=customer["name"],
        vehicle_plate=vehicle["plate_number"],
        session_id=completed_session["session_id"],
        slot_id=slot_id,
        parking_fee=parking_fee,
        duration_minutes=duration_minutes,
        package_type=package_type,
    )


async def checkin_vehicle(
    db: AsyncIOMotorDatabase,
    *,
    request: RFIDScanWithOCRRequest,
    card: Dict[str, Any],
    customer: Dict[str, Any],
    vehicle: Dict[str, Any],
    now: datetime,
) -> Dict[str, Any]:
    """Atomically claim an available slot and create a parking session."""

    session_id = await generate_id(db, "sessions", "S")
    available_slot = await db.parking_slots.find_one_and_update(
        {"status": SlotStatus.AVAILABLE.value},
        {
            "$set": {
                "status": SlotStatus.OCCUPIED.value,
                "vehicle_id": card["vehicle_id"],
                "session_id": session_id,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    if not available_slot:
        return deny("Parking lot is full.", "NO_AVAILABLE_SLOT")

    session = {
        "session_id": session_id,
        "card_uid": request.card_uid.strip(),
        "customer_id": card["customer_id"],
        "vehicle_id": card["vehicle_id"],
        "slot_id": available_slot["slot_id"],
        "entry_gate_id": request.gate_id,
        "exit_gate_id": None,
        "entry_time": now,
        "exit_time": None,
        "distance_cm": request.distance_cm,
        "ocr_plate": normalize_plate(request.ocr_plate),
        "ocr_confidence": request.ocr_confidence,
        "capture_batch_id": request.capture_batch_id,
        "status": SessionStatus.IN_PROGRESS.value,
        "parking_fee": 0.0,
        "created_at": now,
    }

    try:
        await db.sessions.insert_one(session)
    except Exception:
        await db.parking_slots.update_one(
            {
                "slot_id": available_slot["slot_id"],
                "session_id": session_id,
            },
            {
                "$set": {
                    "status": SlotStatus.AVAILABLE.value,
                    "vehicle_id": None,
                    "session_id": None,
                    "updated_at": datetime.now(),
                }
            },
        )
        raise

    return allow(
        "checkin",
        "Vehicle checked in successfully.",
        gate_id=request.gate_id,
        device_id=request.device_id.strip(),
        customer_name=customer["name"],
        vehicle_plate=vehicle["plate_number"],
        session_id=session_id,
        slot_id=available_slot["slot_id"],
    )
