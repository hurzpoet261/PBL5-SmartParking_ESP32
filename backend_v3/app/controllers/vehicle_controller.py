"""
Vehicle Controller
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
from datetime import datetime

from app.database import get_database
from app.utils.id_generator import generate_id
from app.utils.serializers import serialize_mongodb_document, serialize_list
from app.models.vehicle import VehicleCreate, VehicleUpdate

router = APIRouter()


@router.get("")
async def get_vehicles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    vehicle_type: Optional[str] = None,
    customer_id: Optional[str] = None,
    plate_number: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get list of vehicles"""
    query = {}
    
    if vehicle_type:
        query["vehicle_type"] = vehicle_type
    
    if customer_id:
        query["customer_id"] = customer_id

    if plate_number:
        query["plate_number"] = {"$regex": plate_number, "$options": "i"}
    
    total = await db.vehicles.count_documents(query)
    vehicles = await db.vehicles.find(query).skip(skip).limit(limit).to_list(length=limit)

    enriched_vehicles = []
    for vehicle in vehicles:
        customer = await db.customers.find_one({"customer_id": vehicle.get("customer_id")})
        enriched_vehicles.append({
            **serialize_mongodb_document(vehicle),
            "customer_name": customer.get("name") if customer else "N/A"
        })
    
    return {
        "success": True,
        "total": total,
        "data": serialize_list(enriched_vehicles)
    }


@router.post("")
async def create_vehicle(vehicle: VehicleCreate, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Create new vehicle"""
    # Check if plate number exists
    existing = await db.vehicles.find_one({"plate_number": vehicle.plate_number})
    if existing:
        raise HTTPException(status_code=400, detail="Plate number already exists")
    
    vehicle_id = await generate_id(db, "vehicles", "V")
    
    new_vehicle = {
        "vehicle_id": vehicle_id,
        "customer_id": vehicle.customer_id,
        "plate_number": vehicle.plate_number,
        "vehicle_type": vehicle.vehicle_type.value,
        "brand": vehicle.brand,
        "model": vehicle.model,
        "color": vehicle.color,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "is_active": True
    }
    
    await db.vehicles.insert_one(new_vehicle)
    
    return {
        "success": True,
        "message": "Vehicle created successfully",
        "data": serialize_mongodb_document(new_vehicle)
    }


@router.put("/{vehicle_id}")
async def update_vehicle(
    vehicle_id: str,
    vehicle: VehicleUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update vehicle"""
    existing = await db.vehicles.find_one({"vehicle_id": vehicle_id})
    
    if not existing:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    update_data = {k: v for k, v in vehicle.dict(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = datetime.now()
    
    await db.vehicles.update_one(
        {"vehicle_id": vehicle_id},
        {"$set": update_data}
    )
    
    updated = await db.vehicles.find_one({"vehicle_id": vehicle_id})
    
    return {
        "success": True,
        "message": "Vehicle updated successfully",
        "data": serialize_mongodb_document(updated)
    }
