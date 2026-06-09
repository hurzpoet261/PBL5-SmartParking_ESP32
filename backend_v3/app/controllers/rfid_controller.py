"""
RFID Controller.

Current production access flow is locked to:
RFID MQTT -> camera_bridge.py -> POST /api/v1/access-events/rfid-camera.

POST /api/v1/rfid/scan is kept only for registration/test compatibility.
It never creates parking sessions, never calculates fee, and never grants gate access.
"""
import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_database
from app.utils.serializers import serialize_mongodb_document
from app.utils.timezone import iso_local, now_local

logger = logging.getLogger(__name__)

router = APIRouter()

ACCESS_EVENT_ENDPOINT = "/api/v1/access-events/rfid-camera"
VALID_CARD_STATUSES = {"active", "inactive", "lost", "expired"}

REGISTRATION_MODE = {
    "enabled": False,
    "started_at": None,
}


class RFIDScanRequest(BaseModel):
    """RFID scan request from legacy/test clients."""

    card_uid: str = Field(..., description="Card UID")
    gate_id: int = Field(1, description="Gate ID")
    distance_cm: Optional[float] = Field(None, description="Distance from ultrasonic sensor")
    timestamp: Optional[float] = Field(
        None,
        description="Device timestamp; server time is authoritative",
    )


def normalize_card_uid(card_uid: object) -> str:
    """Normalize RFID UID for stable duplicate checks."""

    return str(card_uid or "").strip().lower()


async def find_card_by_uid(db: AsyncIOMotorDatabase, card_uid: str) -> Optional[dict]:
    """Find a card by UID while tolerating older mixed-case data."""

    normalized_uid = normalize_card_uid(card_uid)
    if not normalized_uid:
        return None

    card = await db.rfid_cards.find_one({"card_uid": normalized_uid})
    if card:
        return card

    return await db.rfid_cards.find_one(
        {
            "card_uid": {
                "$regex": f"^{re.escape(normalized_uid)}$",
                "$options": "i",
            }
        }
    )


async def validate_card_binding(
    db: AsyncIOMotorDatabase,
    *,
    card_uid: str,
    customer_id: str,
    vehicle_id: str,
    status: str,
) -> tuple[dict, dict]:
    """Validate customer-vehicle-card relationship before saving a card."""

    if not card_uid:
        raise HTTPException(status_code=400, detail="card_uid is required")
    if not customer_id:
        raise HTTPException(status_code=400, detail="customer_id is required")
    if not vehicle_id:
        raise HTTPException(status_code=400, detail="vehicle_id is required")
    if status not in VALID_CARD_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid card status")

    existing = await find_card_by_uid(db, card_uid)
    if existing:
        raise HTTPException(status_code=400, detail="Card UID already registered")

    customer = await db.customers.find_one({"customer_id": customer_id, "is_active": True})
    if not customer:
        raise HTTPException(status_code=404, detail="Active customer not found")

    vehicle = await db.vehicles.find_one(
        {
            "vehicle_id": vehicle_id,
            "customer_id": customer_id,
            "is_active": True,
        }
    )
    if not vehicle:
        raise HTTPException(
            status_code=400,
            detail="Vehicle must exist, be active, and belong to the selected customer",
        )

    if status == "active":
        active_card = await db.rfid_cards.find_one(
            {
                "vehicle_id": vehicle_id,
                "status": "active",
            }
        )
        if active_card:
            raise HTTPException(status_code=400, detail="Vehicle already has an active RFID card")

    return customer, vehicle


@router.post("/registration-mode/start")
async def start_registration_mode(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Enable registration mode so new RFID scans are reserved for web registration."""

    REGISTRATION_MODE["enabled"] = True
    REGISTRATION_MODE["started_at"] = iso_local()
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
    """Return current registration-mode state."""

    return {
        "success": True,
        "enabled": REGISTRATION_MODE["enabled"],
        "started_at": REGISTRATION_MODE["started_at"],
    }


@router.get("/latest-scan")
async def get_latest_scan(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get the latest card UID captured while registration mode was enabled."""

    latest = await db.pending_scans.find_one({}, sort=[("scanned_at", -1)])
    if not latest:
        return {
            "success": False,
            "message": "No RFID card has been scanned for registration yet.",
        }

    existing_card = await find_card_by_uid(db, latest["card_uid"])
    return {
        "success": True,
        "card_uid": latest["card_uid"],
        "scanned_at": latest["scanned_at"].isoformat(),
        "gate_id": latest.get("gate_id", 1),
        "already_registered": bool(existing_card),
    }


@router.delete("/latest-scan")
async def clear_latest_scan(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Clear pending registration scans."""

    result = await db.pending_scans.delete_many({})
    return {
        "success": True,
        "deleted_count": result.deleted_count,
    }


@router.post("/register-card")
async def register_card(card_data: dict, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Register a new RFID card after validating the customer and vehicle binding."""

    dt = now_local()
    card_uid = normalize_card_uid(card_data.get("card_uid"))
    customer_id = str(card_data.get("customer_id") or "").strip()
    vehicle_id = str(card_data.get("vehicle_id") or "").strip()
    status = str(card_data.get("status") or "active").strip().lower()

    await validate_card_binding(
        db,
        card_uid=card_uid,
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        status=status,
    )

    card_doc = {
        "card_uid": card_uid,
        "customer_id": customer_id,
        "vehicle_id": vehicle_id,
        "status": status,
        "issued_at": dt,
        "expire_at": None,
        "created_at": dt,
        "notes": "Registered from web",
    }

    await db.rfid_cards.insert_one(card_doc)

    return {
        "success": True,
        "message": "RFID card registered successfully",
        "data": serialize_mongodb_document(card_doc),
    }


@router.post("/scan")
async def rfid_scan(request: RFIDScanRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Registration/test-only RFID endpoint.

    This endpoint intentionally does not perform entry/exit decisions. It exists so
    the registration page can capture card UIDs and so old test clients receive a
    clear response telling them to use the camera/OCR flow.
    """

    card_uid = normalize_card_uid(request.card_uid)
    if not card_uid:
        raise HTTPException(status_code=400, detail="card_uid is required")

    dt = now_local()
    card = await find_card_by_uid(db, card_uid)

    if REGISTRATION_MODE["enabled"]:
        await db.pending_scans.insert_one(
            {
                "card_uid": card_uid,
                "gate_id": request.gate_id,
                "distance_cm": request.distance_cm,
                "scanned_at": dt,
            }
        )
        logger.info("[RFID] Registration scan saved: %s", card_uid)
        return {
            "success": False,
            "registration_saved": True,
            "action": "pending_registration",
            "open_gate": False,
            "message": "Card UID saved for registration. Gate access is disabled on /rfid/scan.",
            "card_uid": card_uid,
            "already_registered": bool(card),
        }

    active_session = None
    customer = None
    vehicle = None
    if card:
        active_session = await db.sessions.find_one(
            {
                "card_uid": card.get("card_uid", card_uid),
                "status": "in_progress",
            }
        )
        customer = await db.customers.find_one({"customer_id": card.get("customer_id")})
        vehicle = await db.vehicles.find_one({"vehicle_id": card.get("vehicle_id")})

    logger.info("[RFID] /rfid/scan called in test mode only: %s", card_uid)
    return {
        "success": False,
        "registration_saved": False,
        "action": "camera_flow_required" if card else "walk_in_requires_camera",
        "open_gate": False,
        "message": "Gate operation is locked to the camera/OCR access-event flow.",
        "card_uid": card_uid,
        "registered": bool(card),
        "card_status": card.get("status") if card else None,
        "customer_id": card.get("customer_id") if card else None,
        "customer_name": customer.get("name") if customer else None,
        "vehicle_id": card.get("vehicle_id") if card else None,
        "vehicle_plate": vehicle.get("plate_number") if vehicle else None,
        "active_session": bool(active_session),
        "expected_camera_action": "exit" if active_session else "entry",
        "access_endpoint": ACCESS_EVENT_ENDPOINT,
    }
