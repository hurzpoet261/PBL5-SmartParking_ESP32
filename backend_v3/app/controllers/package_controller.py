"""Package controller."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.models.package import Package, PackageCreate
from app.services.fee_calculator import FeeCalculator
from app.utils.id_generator import generate_id
from app.utils.serializers import serialize_list, serialize_mongodb_document

router = APIRouter()


@router.get("")
async def get_packages(
    customer_id: Optional[str] = None,
    package_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get package list with customer and vehicle details."""

    query = {}
    if customer_id:
        query["customer_id"] = customer_id
    if package_type:
        query["package_type"] = package_type
    if status:
        query["status"] = status

    packages = await db.packages.find(query).sort("created_at", -1).to_list(length=1000)
    enriched_packages = []
    for package in packages:
        customer = await db.customers.find_one({"customer_id": package.get("customer_id")})
        vehicle = await db.vehicles.find_one({"vehicle_id": package.get("vehicle_id")})
        enriched_packages.append(
            {
                **serialize_mongodb_document(package),
                "customer_name": customer.get("name") if customer else "N/A",
                "plate_number": vehicle.get("plate_number") if vehicle else "N/A",
                "end_date": package.get("expire_date"),
                "is_active": package.get("status") == "active",
            }
        )

    return {
        "success": True,
        "total": len(enriched_packages),
        "data": serialize_list(enriched_packages),
    }


@router.post("")
async def create_package(
    package: PackageCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Create a vehicle-bound package and its purchase transaction."""

    customer = await db.customers.find_one({"customer_id": package.customer_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    vehicle = await db.vehicles.find_one({"vehicle_id": package.vehicle_id})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    if vehicle.get("customer_id") != package.customer_id:
        raise HTTPException(
            status_code=400,
            detail="Vehicle does not belong to the selected customer",
        )

    if not customer.get("is_active", True) or not vehicle.get("is_active", True):
        raise HTTPException(
            status_code=400,
            detail="Customer and vehicle must be active",
        )

    package_id = await generate_id(db, "packages", "P")
    price = FeeCalculator.get_package_price(
        package.package_type,
        package.remaining_uses,
    )
    start_date = datetime.now()
    expire_date = Package.calculate_expire_date(package.package_type, start_date)
    new_package = {
        "package_id": package_id,
        "customer_id": package.customer_id,
        "vehicle_id": package.vehicle_id,
        "vehicle_type": vehicle.get("vehicle_type"),
        "package_type": package.package_type.value,
        "price": price,
        "start_date": start_date,
        "expire_date": expire_date,
        "remaining_uses": package.remaining_uses,
        "consumed_session_ids": [],
        "status": "active",
        "created_at": start_date,
    }
    await db.packages.insert_one(new_package)

    transaction_id = await generate_id(db, "transactions", "T")
    await db.transactions.insert_one(
        {
            "transaction_id": transaction_id,
            "customer_id": package.customer_id,
            "transaction_type": "package_purchase",
            "amount": price,
            "package_id": package_id,
            "payment_method": "cash",
            "description": f"Package purchase - {package.package_type.value}",
            "created_at": start_date,
        }
    )
    return {
        "success": True,
        "message": "Package created successfully",
        "data": serialize_mongodb_document(new_package),
    }


@router.get("/types")
async def get_package_types():
    """Get available vehicle-bound package types and prices."""

    from app.config import settings

    return {
        "success": True,
        "data": [
            {
                "type": "per_use",
                "name": "Prepaid uses",
                "price": settings.FEE_PER_HOUR,
                "unit": "VND/use",
                "description": "Finite package; one prepaid use is consumed per checkout",
            },
            {
                "type": "daily",
                "name": "Daily",
                "price": settings.FEE_DAILY_PACKAGE,
                "unit": "VND/day",
                "description": "Unlimited parking for the registered vehicle during one day",
            },
            {
                "type": "monthly",
                "name": "Monthly",
                "price": settings.FEE_MONTHLY_PACKAGE,
                "unit": "VND/month",
                "description": "Unlimited parking for the registered vehicle during 30 days",
            },
        ],
    }
