"""
Session Controller
"""
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional

from app.database import get_database

router = APIRouter()


@router.get("")
async def get_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get list of sessions"""
    query = {}
    
    if status:
        query["status"] = status
    
    if customer_id:
        query["customer_id"] = customer_id
    
    total = await db.sessions.count_documents(query)
    sessions = await db.sessions.find(query).sort("entry_time", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return {
        "success": True,
        "total": total,
        "data": sessions
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
            **session,
            "customer": customer,
            "vehicle": vehicle
        }
    }
