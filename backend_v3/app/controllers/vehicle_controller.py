"""
Vehicle Controller.

Vehicle records are owned by one active customer. Plate numbers are normalized
before saving so OCR, registration, and duplicate checks use the same format.
"""
from datetime import datetime
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.models.vehicle import VehicleCreate, VehicleUpdate
from app.utils.id_generator import generate_id
from app.utils.serializers import serialize_list, serialize_mongodb_document

router = APIRouter()


def normalize_plate_number(plate_number: object) -> str:
    """Normalize license plate text for storage and duplicate checks."""

    plate = str(plate_number or "").strip().upper()
    plate = re.sub(r"[^0-9A-Z]", "", plate)
    if len(plate) >= 2:
        # Vietnam plates start with province digits; correct common OCR-like input.
        prefix = plate[:2].replace("O", "0").replace("I", "1").replace("L", "1")
        plate = prefix + plate[2:]
    return plate


async def find_vehicle_by_normalized_plate(
    db: AsyncIOMotorDatabase,
    normalized_plate: str,
) -> Optional[dict]:
    """Find an existing vehicle whose stored plate normalizes to the same value."""

    direct = await db.vehicles.find_one({"plate_number": normalized_plate})
    if direct:
        return direct

    async for vehicle in db.vehicles.find({"plate_number": {"$exists": True}}):
        if normalize_plate_number(vehicle.get("plate_number")) == normalized_plate:
            return vehicle

    return None


@router.get("")
async def get_vehicles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    vehicle_type: Optional[str] = None,
    customer_id: Optional[str] = None,
    plate_number: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get list of vehicles."""

    query = {}

    if vehicle_type:
        query["vehicle_type"] = vehicle_type

    if customer_id:
        query["customer_id"] = customer_id

    if plate_number:
        normalized_filter = normalize_plate_number(plate_number)
        query["$or"] = [
            {"plate_number": {"$regex": re.escape(str(plate_number)), "$options": "i"}},
            {"plate_number": {"$regex": re.escape(normalized_filter), "$options": "i"}},
        ]

    total = await db.vehicles.count_documents(query)
    vehicles = await db.vehicles.find(query).skip(skip).limit(limit).to_list(length=limit)

    enriched_vehicles = []
    for vehicle in vehicles:
        customer = await db.customers.find_one({"customer_id": vehicle.get("customer_id")})
        enriched_vehicles.append(
            {
                **serialize_mongodb_document(vehicle),
                "customer_name": customer.get("name") if customer else "N/A",
            }
        )

    return {
        "success": True,
        "total": total,
        "data": serialize_list(enriched_vehicles),
    }


@router.post("")
async def create_vehicle(vehicle: VehicleCreate, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Create a vehicle for an active customer."""

    customer = await db.customers.find_one({"customer_id": vehicle.customer_id, "is_active": True})
    if not customer:
        raise HTTPException(status_code=404, detail="Active customer not found")

    plate_number = normalize_plate_number(vehicle.plate_number)
    if not plate_number:
        raise HTTPException(status_code=400, detail="Plate number is required")

    existing = await find_vehicle_by_normalized_plate(db, plate_number)
    if existing:
        raise HTTPException(status_code=400, detail="Plate number already exists")

    vehicle_id = await generate_id(db, "vehicles", "V")
    dt = datetime.now()

    new_vehicle = {
        "vehicle_id": vehicle_id,
        "customer_id": vehicle.customer_id,
        "plate_number": plate_number,
        "vehicle_type": vehicle.vehicle_type.value,
        "brand": vehicle.brand,
        "model": vehicle.model,
        "color": vehicle.color,
        "created_at": dt,
        "updated_at": dt,
        "is_active": True,
    }

    await db.vehicles.insert_one(new_vehicle)

    return {
        "success": True,
        "message": "Vehicle created successfully",
        "data": serialize_mongodb_document(new_vehicle),
    }


@router.put("/{vehicle_id}")
async def update_vehicle(
    vehicle_id: str,
    vehicle: VehicleUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Update vehicle."""

    existing = await db.vehicles.find_one({"vehicle_id": vehicle_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    update_data = vehicle.model_dump(exclude_unset=True)

    if "plate_number" in update_data:
        plate_number = normalize_plate_number(update_data["plate_number"])
        if not plate_number:
            raise HTTPException(status_code=400, detail="Plate number is required")

        duplicate = await find_vehicle_by_normalized_plate(db, plate_number)
        if duplicate and duplicate.get("vehicle_id") != vehicle_id:
            raise HTTPException(status_code=400, detail="Plate number already exists")

        update_data["plate_number"] = plate_number

    if "vehicle_type" in update_data:
        if update_data["vehicle_type"] is None:
            update_data.pop("vehicle_type")
        else:
            update_data["vehicle_type"] = update_data["vehicle_type"].value

    update_data["updated_at"] = datetime.now()

    await db.vehicles.update_one({"vehicle_id": vehicle_id}, {"$set": update_data})

    updated = await db.vehicles.find_one({"vehicle_id": vehicle_id})
    return {
        "success": True,
        "message": "Vehicle updated successfully",
        "data": serialize_mongodb_document(updated),
    }
