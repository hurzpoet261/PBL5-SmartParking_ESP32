"""
Session Controller
"""
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional

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
    
    total = await db.sessions.count_documents(query)
    sessions = await db.sessions.find(query).sort("entry_time", -1).skip(skip).limit(limit).to_list(length=limit)
    
    # Enrich with customer and vehicle info
    enriched_sessions = []
    for session in sessions:
        fix_id(session)
        
        customer = await db.customers.find_one({"customer_id": session.get("customer_id")})
        fix_id(customer)

        vehicle = await db.vehicles.find_one({"vehicle_id": session.get("vehicle_id")})
        fix_id(vehicle)

        slot = await db.parking_slots.find_one({"slot_id": session.get("slot_id")})
        fix_id(slot)
        
        enriched_session = {
            **session,
            "customer_name": customer.get("name") if customer else "N/A",
            "plate_number": vehicle.get("plate_number") if vehicle else "N/A",
            "slot_number": slot.get("slot_number") if slot else session.get("slot_id", "N/A"),
            "check_in_time": session.get("entry_time"),  # Alias for compatibility
            "check_out_time": session.get("exit_time"),
            "fee": session.get("parking_fee", 0)
        }
        enriched_sessions.append(enriched_session)
    
    # Filter by plate_number if provided (after enrichment)
    if plate_number:
        enriched_sessions = [s for s in enriched_sessions if plate_number.lower() in s.get("plate_number", "").lower()]
        total = len(enriched_sessions)
    
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
