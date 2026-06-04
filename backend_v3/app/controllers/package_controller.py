"""
Package Controller.

Business rule:
- per_use is only a billing mode for sessions without a valid package.
- Stored packages are daily/monthly subscriptions tied to one active vehicle.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.models.package import Package, PackageCreate, PackageType
from app.services.fee_calculator import FeeCalculator
from app.utils.id_generator import generate_id
from app.utils.serializers import serialize_list, serialize_mongodb_document

router = APIRouter()

STORED_PACKAGE_TYPES = [PackageType.DAILY.value, PackageType.MONTHLY.value]


@router.get("")
async def get_packages(
    customer_id: Optional[str] = None,
    package_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get list of stored packages."""

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
async def create_package(package: PackageCreate, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Create a daily/monthly package for a customer's active vehicle."""

    if package.package_type == PackageType.PER_USE:
        raise HTTPException(
            status_code=400,
            detail="per_use is a billing mode, not a stored package",
        )

    customer = await db.customers.find_one({"customer_id": package.customer_id, "is_active": True})
    if not customer:
        raise HTTPException(status_code=404, detail="Active customer not found")

    vehicle = await db.vehicles.find_one(
        {
            "vehicle_id": package.vehicle_id,
            "customer_id": package.customer_id,
            "is_active": True,
        }
    )
    if not vehicle:
        raise HTTPException(
            status_code=400,
            detail="Vehicle must exist, be active, and belong to the selected customer",
        )

    active_existing = await db.packages.find_one(
        {
            "vehicle_id": package.vehicle_id,
            "status": "active",
            "package_type": {"$in": STORED_PACKAGE_TYPES},
            "expire_date": {"$gt": datetime.now()},
        }
    )
    if active_existing:
        raise HTTPException(status_code=400, detail="Vehicle already has an active package")

    package_id = await generate_id(db, "packages", "P")

    price = FeeCalculator.get_package_price(package.package_type)
    start_date = datetime.now()
    expire_date = Package.calculate_expire_date(package.package_type, start_date)

    new_package = {
        "package_id": package_id,
        "customer_id": package.customer_id,
        "vehicle_id": package.vehicle_id,
        "package_type": package.package_type.value,
        "price": price,
        "start_date": start_date,
        "expire_date": expire_date,
        "remaining_uses": package.remaining_uses,
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
    """Get available billing/package types and prices."""

    from app.config import settings

    return {
        "success": True,
        "data": [
            {
                "type": "per_use",
                "name": "Theo luot",
                "price": settings.FEE_PER_HOUR,
                "unit": "VND/hour",
                "description": "Session fee calculated by parking duration",
                "creates_package": False,
            },
            {
                "type": "daily",
                "name": "Theo ngay",
                "price": settings.FEE_DAILY_PACKAGE,
                "unit": "VND/day",
                "description": "Unlimited parking for 1 day",
                "creates_package": True,
            },
            {
                "type": "monthly",
                "name": "Theo thang",
                "price": settings.FEE_MONTHLY_PACKAGE,
                "unit": "VND/month",
                "description": "Unlimited parking for 30 days",
                "creates_package": True,
            },
        ],
    }
