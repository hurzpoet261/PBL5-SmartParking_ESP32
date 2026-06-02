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

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.database import get_database
from app.controllers.registration_controller import RegisterCardRequest, card_uid_variants
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
    capture_batch_id: str = Field(
        ...,
        min_length=1,
        description="Unique OCR capture batch used as the idempotency key",
    )


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
    card_data: RegisterCardRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Register a new RFID card from the existing web form."""

    card_uid = card_data.card_uid
    customer_id = card_data.customer_id.strip()
    vehicle_id = card_data.vehicle_id.strip()
    status = card_data.status.value

    if not customer_id or not vehicle_id:
        raise HTTPException(
            status_code=422,
            detail="customer_id and vehicle_id cannot be blank",
        )

    existing = await db.rfid_cards.find_one(
        {"card_uid": {"$in": card_uid_variants(card_uid)}}
    )
    if existing:
        raise HTTPException(status_code=409, detail="RFID card UID already exists")

    customer = await db.customers.find_one({"customer_id": customer_id})
    vehicle = await db.vehicles.find_one({"vehicle_id": vehicle_id})
    if not customer or not vehicle or vehicle.get("customer_id") != customer_id:
        raise HTTPException(status_code=400, detail="Invalid customer and vehicle binding")

    now = datetime.now()
    card_doc = {
        "card_uid": card_uid,
        "customer_id": customer_id,
        "vehicle_id": vehicle_id,
        "status": status,
        "issued_at": now,
        "expire_at": card_data.expire_at,
        "created_at": now,
        "notes": card_data.notes or "Registered from compatibility endpoint",
    }
    try:
        await db.rfid_cards.insert_one(card_doc)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="RFID card UID already exists") from exc

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

    request_id = request.capture_batch_id.strip()
    if not request_id:
        return deny("Capture batch ID is empty.", "CAPTURE_BATCH_ID_EMPTY")

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

    processed_session = await db.sessions.find_one(
        {
            "card_uid": card_uid,
            "vehicle_id": card["vehicle_id"],
            "$or": [
                {"checkin_request_id": request_id},
                {"checkout_request_id": request_id},
                {"capture_batch_id": request_id},
            ],
        }
    )
    if processed_session:
        if processed_session.get("checkout_request_id") == request_id:
            return await build_checkout_response(
                db,
                request=request,
                customer=customer,
                vehicle=vehicle,
                completed_session=processed_session,
                now=now,
                idempotent=True,
            )
        return build_checkin_response(
            request=request,
            customer=customer,
            vehicle=vehicle,
            session=processed_session,
            idempotent=True,
        )

    active_session = await db.sessions.find_one(
        {
            "status": SessionStatus.IN_PROGRESS.value,
            "$or": [
                {"card_uid": card_uid},
                {"vehicle_id": card["vehicle_id"]},
            ],
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

    base_fee = FeeCalculator.calculate_base_fee(
        active_session["entry_time"],
        now,
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
                "parking_fee": base_fee,
                "checkout_request_id": request.capture_batch_id.strip(),
            }
        },
        return_document=ReturnDocument.BEFORE,
    )
    closed_now = completed_session is not None
    if not completed_session:
        completed_session = await db.sessions.find_one(
            {
                "session_id": active_session["session_id"],
                "status": SessionStatus.COMPLETED.value,
            }
        )
    if not completed_session:
        return deny(
            "Parking session is no longer active.",
            "SESSION_NOT_ACTIVE",
        )

    if closed_now:
        completed_session.update(
            {
                "exit_time": now,
                "exit_gate_id": request.gate_id,
                "parking_fee": base_fee,
                "checkout_request_id": request.capture_batch_id.strip(),
                "status": SessionStatus.COMPLETED.value,
            }
        )

    return await build_checkout_response(
        db,
        request=request,
        customer=customer,
        vehicle=vehicle,
        completed_session=completed_session,
        now=now,
        idempotent=not closed_now,
    )


def eligible_package_query(
    *,
    customer_id: str,
    vehicle_id: str,
    vehicle_type: Optional[str],
    at_time: datetime,
) -> Dict[str, Any]:
    """Limit package application to the registered customer and vehicle."""

    query: Dict[str, Any] = {
        "customer_id": customer_id,
        "vehicle_id": vehicle_id,
        "status": "active",
        "expire_date": {"$gt": at_time},
    }
    if vehicle_type:
        query["$or"] = [
            {"vehicle_type": {"$exists": False}},
            {"vehicle_type": None},
            {"vehicle_type": vehicle_type},
        ]
    return query


async def resolve_checkout_fee_breakdown(
    db: AsyncIOMotorDatabase,
    *,
    completed_session: Dict[str, Any],
    vehicle: Dict[str, Any],
) -> Dict[str, Any]:
    """Resolve an eligible vehicle package and atomically consume prepaid use."""

    exit_time = completed_session["exit_time"]
    query = eligible_package_query(
        customer_id=completed_session["customer_id"],
        vehicle_id=completed_session["vehicle_id"],
        vehicle_type=vehicle.get("vehicle_type"),
        at_time=exit_time,
    )

    unlimited_package = await db.packages.find_one(
        {
            **query,
            "package_type": {"$in": ["daily", "monthly"]},
        }
    )
    if unlimited_package:
        return FeeCalculator.build_fee_breakdown(
            completed_session["entry_time"],
            exit_time,
            unlimited_package,
        )

    session_id = completed_session["session_id"]
    per_use_package = await db.packages.find_one_and_update(
        {
            **query,
            "package_type": "per_use",
            "remaining_uses": {"$gt": 0},
            "consumed_session_ids": {"$ne": session_id},
        },
        {
            "$inc": {"remaining_uses": -1},
            "$addToSet": {"consumed_session_ids": session_id},
        },
        return_document=ReturnDocument.AFTER,
    )
    if not per_use_package:
        per_use_package = await db.packages.find_one(
            {
                **query,
                "package_type": "per_use",
                "consumed_session_ids": session_id,
            }
        )

    return FeeCalculator.build_fee_breakdown(
        completed_session["entry_time"],
        exit_time,
        per_use_package,
    )


async def finalize_session_fee(
    db: AsyncIOMotorDatabase,
    *,
    completed_session: Dict[str, Any],
    vehicle: Dict[str, Any],
) -> Dict[str, Any]:
    """Persist one auditable fee result, repairing an interrupted checkout."""

    if completed_session.get("fee_breakdown"):
        return completed_session

    fee_breakdown = await resolve_checkout_fee_breakdown(
        db,
        completed_session=completed_session,
        vehicle=vehicle,
    )
    await db.sessions.update_one(
        {
            "session_id": completed_session["session_id"],
            "$or": [
                {"fee_breakdown": {"$exists": False}},
                {"fee_breakdown": None},
            ],
        },
        {
            "$set": {
                "parking_fee": fee_breakdown["final_fee"],
                "package_id": fee_breakdown.get("package_id"),
                "package_type": fee_breakdown.get("package_type"),
                "fee_breakdown": fee_breakdown,
            }
        },
    )
    finalized_session = await db.sessions.find_one(
        {"session_id": completed_session["session_id"]}
    )
    return finalized_session or {
        **completed_session,
        "parking_fee": fee_breakdown["final_fee"],
        "package_id": fee_breakdown.get("package_id"),
        "package_type": fee_breakdown.get("package_type"),
        "fee_breakdown": fee_breakdown,
    }


async def ensure_parking_fee_transaction(
    db: AsyncIOMotorDatabase,
    *,
    completed_session: Dict[str, Any],
    now: datetime,
) -> Optional[Dict[str, Any]]:
    """Create at most one parking fee transaction for a completed session."""

    parking_fee = float(completed_session.get("parking_fee") or 0)
    fee_breakdown = completed_session.get("fee_breakdown") or {
        "base_fee": parking_fee,
        "discount": 0.0,
        "package_applied": False,
        "package_id": None,
        "final_fee": parking_fee,
        "reason": "Legacy session without persisted fee breakdown.",
    }

    session_id = completed_session["session_id"]
    existing = await db.transactions.find_one(
        {
            "transaction_type": "parking_fee",
            "session_id": session_id,
        }
    )
    if existing:
        return existing

    transaction_id = await generate_id(db, "transactions", "T")
    transaction = {
        "transaction_id": transaction_id,
        "customer_id": completed_session["customer_id"],
        "transaction_type": "parking_fee",
        "amount": parking_fee,
        "session_id": session_id,
        "parking_fee_session_id": session_id,
        "package_id": fee_breakdown.get("package_id"),
        "fee_breakdown": fee_breakdown,
        "payment_method": "cash",
        "description": f"Parking fee - {session_id}",
        "created_at": now,
    }
    try:
        await db.transactions.update_one(
            {"parking_fee_session_id": session_id},
            {"$setOnInsert": transaction},
            upsert=True,
        )
    except DuplicateKeyError:
        pass

    return await db.transactions.find_one({"parking_fee_session_id": session_id})


async def build_checkout_response(
    db: AsyncIOMotorDatabase,
    *,
    request: RFIDScanWithOCRRequest,
    customer: Dict[str, Any],
    vehicle: Dict[str, Any],
    completed_session: Dict[str, Any],
    now: datetime,
    idempotent: bool,
) -> Dict[str, Any]:
    """Return checkout response and repair a missing fee transaction on retry."""

    completed_session = await finalize_session_fee(
        db,
        completed_session=completed_session,
        vehicle=vehicle,
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

    await ensure_parking_fee_transaction(
        db,
        completed_session=completed_session,
        now=now,
    )
    exit_time = completed_session.get("exit_time") or now
    duration_minutes = round(
        (exit_time - completed_session["entry_time"]).total_seconds() / 60
    )
    return allow(
        "checkout",
        "Vehicle checkout already completed." if idempotent else "Vehicle checked out successfully.",
        gate_id=request.gate_id,
        device_id=request.device_id.strip(),
        customer_name=customer["name"],
        vehicle_plate=vehicle["plate_number"],
        session_id=completed_session["session_id"],
        slot_id=slot_id,
        parking_fee=float(completed_session.get("parking_fee") or 0),
        duration_minutes=duration_minutes,
        package_type=completed_session.get("package_type"),
        fee_breakdown=completed_session.get("fee_breakdown"),
        idempotent=idempotent,
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

    existing_session = await db.sessions.find_one(
        {
            "status": SessionStatus.IN_PROGRESS.value,
            "$or": [
                {"card_uid": request.card_uid.strip()},
                {"vehicle_id": card["vehicle_id"]},
            ],
        }
    )
    if existing_session:
        return deny(
            "Card or vehicle already has an active parking session.",
            "ACTIVE_SESSION_ALREADY_EXISTS",
            session_id=existing_session["session_id"],
        )

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
        "checkin_request_id": request.capture_batch_id.strip(),
        "status": SessionStatus.IN_PROGRESS.value,
        "parking_fee": 0.0,
        "created_at": now,
    }

    try:
        await db.sessions.insert_one(session)
    except DuplicateKeyError:
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
        existing_session = await db.sessions.find_one(
            {
                "status": SessionStatus.IN_PROGRESS.value,
                "$or": [
                    {"card_uid": request.card_uid.strip()},
                    {"vehicle_id": card["vehicle_id"]},
                ],
            }
        )
        if (
            existing_session
            and existing_session.get("checkin_request_id") == request.capture_batch_id.strip()
        ):
            return build_checkin_response(
                request=request,
                customer=customer,
                vehicle=vehicle,
                session=existing_session,
                idempotent=True,
            )
        return deny(
            "Card or vehicle already has an active parking session.",
            "ACTIVE_SESSION_ALREADY_EXISTS",
            session_id=existing_session.get("session_id") if existing_session else None,
        )
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

    return build_checkin_response(
        request=request,
        customer=customer,
        vehicle=vehicle,
        session=session,
        idempotent=False,
    )


def build_checkin_response(
    *,
    request: RFIDScanWithOCRRequest,
    customer: Dict[str, Any],
    vehicle: Dict[str, Any],
    session: Dict[str, Any],
    idempotent: bool,
) -> Dict[str, Any]:
    """Return the original check-in decision for a repeated request."""

    return allow(
        "checkin",
        "Vehicle check-in already completed." if idempotent else "Vehicle checked in successfully.",
        gate_id=request.gate_id,
        device_id=request.device_id.strip(),
        customer_name=customer["name"],
        vehicle_plate=vehicle["plate_number"],
        session_id=session["session_id"],
        slot_id=session["slot_id"],
        idempotent=idempotent,
    )
