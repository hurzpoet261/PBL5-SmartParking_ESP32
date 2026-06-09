"""
Session Controller
"""
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
import re

from app.database import get_database

router = APIRouter()

def fix_id(doc):
    """Chuyển đổi _id từ ObjectId sang str để FastAPI có thể render JSON"""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

@router.get("")
async def get_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    plate_number: Optional[str] = None,
    date: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get list of sessions with customer and vehicle info"""
    query = {}
    
    if status:
        # Map 'active' to 'in_progress' for compatibility
        if status == 'active':
            query["status"] = "in_progress"
        else:
            query["status"] = status
    
    if customer_id:
        query["customer_id"] = customer_id
    
    if date:
        from datetime import datetime
        try:
            target_date = datetime.fromisoformat(date)
            query["entry_time"] = {
                "$gte": target_date.replace(hour=0, minute=0, second=0),
                "$lt": target_date.replace(hour=23, minute=59, second=59)
            }
        except:
            pass

    if plate_number:
        plate_regex = {"$regex": re.escape(plate_number), "$options": "i"}
        vehicles_for_plate = await db.vehicles.find(
            {"plate_number": plate_regex},
            {"vehicle_id": 1},
        ).to_list(length=1000)
        vehicle_ids_for_plate = [vehicle.get("vehicle_id") for vehicle in vehicles_for_plate if vehicle.get("vehicle_id")]
        plate_filters = [
            {"plate_number_snapshot": plate_regex},
            {"entry_plate_ocr": plate_regex},
            {"exit_plate_ocr": plate_regex},
        ]
        if vehicle_ids_for_plate:
            plate_filters.append({"vehicle_id": {"$in": vehicle_ids_for_plate}})
        query["$or"] = plate_filters
    
    total = await db.sessions.count_documents(query)
    sessions = await db.sessions.find(query).sort("entry_time", -1).skip(skip).limit(limit).to_list(length=limit)

    customer_ids = sorted({session.get("customer_id") for session in sessions if session.get("customer_id")})
    vehicle_ids = sorted({session.get("vehicle_id") for session in sessions if session.get("vehicle_id")})
    slot_ids = sorted({session.get("slot_id") for session in sessions if session.get("slot_id")})

    customers = (
        await db.customers.find({"customer_id": {"$in": customer_ids}}).to_list(length=len(customer_ids))
        if customer_ids
        else []
    )
    vehicles = (
        await db.vehicles.find({"vehicle_id": {"$in": vehicle_ids}}).to_list(length=len(vehicle_ids))
        if vehicle_ids
        else []
    )
    slots = (
        await db.parking_slots.find({"slot_id": {"$in": slot_ids}}).to_list(length=len(slot_ids))
        if slot_ids
        else []
    )
    customers_by_id = {customer.get("customer_id"): customer for customer in customers}
    vehicles_by_id = {vehicle.get("vehicle_id"): vehicle for vehicle in vehicles}
    slots_by_id = {slot.get("slot_id"): slot for slot in slots}
    
    # Enrich with customer and vehicle info
    enriched_sessions = []
    for session in sessions:
        fix_id(session)
        
        customer = customers_by_id.get(session.get("customer_id"))
        vehicle = vehicles_by_id.get(session.get("vehicle_id"))
        slot = slots_by_id.get(session.get("slot_id"))
        customer_name = (
            customer.get("name")
            if customer
            else session.get("customer_name_snapshot") or "N/A"
        )
        plate_number = (
            vehicle.get("plate_number")
            if vehicle
            else session.get("plate_number_snapshot")
            or session.get("exit_plate_ocr")
            or session.get("entry_plate_ocr")
            or "N/A"
        )
        
        enriched_session = {
            **session,
            "customer_name": customer_name,
            "plate_number": plate_number,
            "slot_number": slot.get("slot_number") if slot else session.get("slot_id", "N/A"),
            "check_in_time": session.get("entry_time"),  # Alias for compatibility
            "check_out_time": session.get("exit_time"),
            "fee": session.get("parking_fee", 0)
        }
        enriched_sessions.append(enriched_session)
    
    return {
        "success": True,
        "total": total,
        "data": enriched_sessions
    }


@router.get("/{session_id}")
async def get_session(session_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get session details"""
    session = await db.sessions.find_one({"session_id": session_id})
    
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get related data
    customer = await db.customers.find_one({"customer_id": session["customer_id"]})
    vehicle = await db.vehicles.find_one({"vehicle_id": session["vehicle_id"]})
    
    return {
        "success": True,
        "data": {
            **fix_id(session),
            "customer": customer,
            "vehicle": vehicle
        }
    }
