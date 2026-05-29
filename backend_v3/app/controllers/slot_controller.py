"""
Parking Slot Controller
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
from datetime import datetime

from app.database import get_database
from app.config import settings
from app.utils.serializers import serialize_mongodb_document, serialize_list

router = APIRouter()


@router.get("")
async def get_slots(
    status: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all parking slots"""
    query = {}

    if status:
        query["status"] = status

    slots = await db.parking_slots.find(query).sort([("row", 1), ("col", 1)]).to_list(length=1000)

    normalized_slots = []
    for slot in slots:
        serialized = serialize_mongodb_document(slot)
        serialized["slot_number"] = serialized.get("slot_number") or serialized.get("slot_id")
        normalized_slots.append(serialized)

    return {
        "success": True,
        "total": len(normalized_slots),
        "data": normalized_slots
    }


@router.get("/map")
async def get_parking_map(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get parking map layout"""
    slots = await db.parking_slots.find().sort([("row", 1), ("col", 1)]).to_list(length=1000)

    serialized_slots = []
    map_data = {}
    for slot in slots:
        serialized = serialize_mongodb_document(slot)
        serialized["slot_number"] = serialized.get("slot_number") or serialized.get("slot_id")

        row = slot.get("row")
        if row is not None:
            if row not in map_data:
                map_data[row] = []
            map_data[row].append(serialized)

        serialized_slots.append(serialized)

    total_slots = len(slots)
    available = len([s for s in slots if s.get("status") == "available"])
    occupied = len([s for s in slots if s.get("status") == "occupied"])
    reserved = len([s for s in slots if s.get("status") == "reserved"])
    maintenance = len([s for s in slots if s.get("status") == "maintenance"])

    return {
        "success": True,
        "rows": settings.PARKING_ROWS,
        "cols": settings.PARKING_COLS,
        "total_slots": total_slots,
        "statistics": {
            "available": available,
            "occupied": occupied,
            "reserved": reserved,
            "maintenance": maintenance,
            "occupancy_rate": round((occupied / total_slots * 100), 1) if total_slots > 0 else 0
        },
        "data": serialized_slots,
        "map": map_data
    }


@router.get("/{slot_id}")
async def get_slot_detail(slot_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get parking slot detail"""
    slot = await db.parking_slots.find_one({"slot_id": slot_id})

    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    slot_data = serialize_mongodb_document(slot)
    slot_data["slot_number"] = slot_data.get("slot_number") or slot_data.get("slot_id")

    if slot.get("session_id"):
        session = await db.sessions.find_one({"session_id": slot["session_id"]})
        if session:
            customer = await db.customers.find_one({"customer_id": session.get("customer_id")})
            vehicle = await db.vehicles.find_one({"vehicle_id": session.get("vehicle_id")})
            slot_data["current_session"] = serialize_mongodb_document({
                "session_id": session.get("session_id"),
                "customer_name": customer.get("name") if customer else "N/A",
                "plate_number": vehicle.get("plate_number") if vehicle else "N/A",
                "check_in_time": session.get("entry_time")
            })
        else:
            slot_data["current_session"] = None
    else:
        slot_data["current_session"] = None

    return {
        "success": True,
        "data": slot_data
    }


@router.post("/initialize")
async def initialize_slots(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Initialize parking slots (run once)"""
    count = await db.parking_slots.count_documents({})
    if count > 0:
        return {
            "success": False,
            "message": "Slots already initialized"
        }

    slots = []
    for row in range(1, settings.PARKING_ROWS + 1):
        for col in range(1, settings.PARKING_COLS + 1):
            slot_id = f"{chr(64 + row)}{col:02d}"
            slots.append({
                "slot_id": slot_id,
                "slot_number": slot_id,
                "row": row,
                "col": col,
                "status": "available",
                "vehicle_id": None,
                "session_id": None,
                "slot_type": "standard",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })

    await db.parking_slots.insert_many(slots)

    return {
        "success": True,
        "message": f"Initialized {len(slots)} parking slots",
        "total": len(slots)
    }
