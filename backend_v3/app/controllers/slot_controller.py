"""
Parking Slot Controller
"""
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
from datetime import datetime

from app.database import get_database
from app.config import settings

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
    
    return {
        "success": True,
        "total": len(slots),
        "data": slots
    }


@router.get("/map")
async def get_parking_map(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get parking map layout"""
    slots = await db.parking_slots.find().sort([("row", 1), ("col", 1)]).to_list(length=1000)
    
    # Group by row
    map_data = {}
    for slot in slots:
        row = slot["row"]
        if row not in map_data:
            map_data[row] = []
        map_data[row].append(slot)
    
    # Get statistics
    total_slots = len(slots)
    available = len([s for s in slots if s["status"] == "available"])
    occupied = len([s for s in slots if s["status"] == "occupied"])
    reserved = len([s for s in slots if s["status"] == "reserved"])
    maintenance = len([s for s in slots if s["status"] == "maintenance"])
    
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
        "map": map_data
    }


@router.post("/initialize")
async def initialize_slots(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Initialize parking slots (run once)"""
    # Check if already initialized
    count = await db.parking_slots.count_documents({})
    if count > 0:
        return {
            "success": False,
            "message": "Slots already initialized"
        }
    
    # Create slots
    slots = []
    for row in range(1, settings.PARKING_ROWS + 1):
        for col in range(1, settings.PARKING_COLS + 1):
            slot_id = f"{chr(64 + row)}{col:02d}"  # A01, A02, ..., B01, B02, ...
            slots.append({
                "slot_id": slot_id,
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
