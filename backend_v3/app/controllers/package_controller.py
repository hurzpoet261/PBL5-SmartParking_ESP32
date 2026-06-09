"""
Package Controller.

Business rule:
- per_use is only a billing mode for sessions without a valid package.
- Stored packages are daily/monthly subscriptions tied to one active vehicle.
"""
from datetime import timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.database import get_database
from app.models.package import Package, PackageCreate, PackageType
from app.services.fee_calculator import FeeCalculator
from app.utils.id_generator import generate_id
from app.utils.serializers import serialize_list, serialize_mongodb_document
from app.utils.timezone import now_local

router = APIRouter()

STORED_PACKAGE_TYPES = [PackageType.DAILY.value, PackageType.MONTHLY.value]
EXPIRING_SOON_DAYS = 3


class PackageRenewRequest(BaseModel):
    package_type: Optional[PackageType] = None


async def sync_expired_packages(db: AsyncIOMotorDatabase) -> int:
    """Mark active packages as expired when their expire_date has passed."""

    result = await db.packages.update_many(
        {
            "status": "active",
            "package_type": {"$in": STORED_PACKAGE_TYPES},
            "expire_date": {"$lte": now_local()},
        },
        {"$set": {"status": "expired", "updated_at": now_local()}},
    )
    return result.modified_count


async def enrich_packages(db: AsyncIOMotorDatabase, packages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    customer_ids = sorted({package.get("customer_id") for package in packages if package.get("customer_id")})
    vehicle_ids = sorted({package.get("vehicle_id") for package in packages if package.get("vehicle_id")})

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
    customers_by_id = {customer.get("customer_id"): customer for customer in customers}
    vehicles_by_id = {vehicle.get("vehicle_id"): vehicle for vehicle in vehicles}
    dt = now_local()

    enriched_packages = []
    for package in packages:
        customer = customers_by_id.get(package.get("customer_id"))
        vehicle = vehicles_by_id.get(package.get("vehicle_id"))
        expire_date = package.get("expire_date")
        is_active = package.get("status") == "active" and bool(expire_date and expire_date > dt)
        days_remaining = None
        if expire_date:
            days_remaining = max(0, (expire_date - dt).days)

        enriched_packages.append(
            {
                **serialize_mongodb_document(package),
                "customer_name": customer.get("name") if customer else "N/A",
                "customer_phone": customer.get("phone") if customer else "N/A",
                "plate_number": vehicle.get("plate_number") if vehicle else "N/A",
                "vehicle_type": vehicle.get("vehicle_type") if vehicle else "N/A",
                "end_date": package.get("expire_date"),
                "is_active": is_active,
                "days_remaining": days_remaining,
                "is_expiring_soon": is_active and days_remaining is not None and days_remaining <= EXPIRING_SOON_DAYS,
            }
        )

    return enriched_packages


def package_matches_search(package: Dict[str, Any], search: str) -> bool:
    keyword = (search or "").strip().lower()
    if not keyword:
        return True

    searchable = [
        package.get("package_id"),
        package.get("customer_id"),
        package.get("customer_name"),
        package.get("customer_phone"),
        package.get("vehicle_id"),
        package.get("plate_number"),
    ]
    return any(keyword in str(value or "").lower() for value in searchable)


@router.get("")
async def get_packages(
    customer_id: Optional[str] = None,
    package_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get list of stored packages."""

    await sync_expired_packages(db)
    dt = now_local()
    query = {}

    if customer_id:
        query["customer_id"] = customer_id

    if package_type:
        query["package_type"] = package_type

    if status:
        if status == "active":
            query["status"] = "active"
            query["expire_date"] = {"$gt": dt}
        elif status == "expired":
            query["status"] = "expired"
        elif status == "expiring_soon":
            query["status"] = "active"
            query["expire_date"] = {"$gt": dt, "$lte": dt + timedelta(days=EXPIRING_SOON_DAYS)}
        elif status == "cancelled":
            query["status"] = "cancelled"
        else:
            query["status"] = status

    packages = await db.packages.find(query).sort("created_at", -1).to_list(length=1000)
    enriched_packages = await enrich_packages(db, packages)

    if search:
        enriched_packages = [package for package in enriched_packages if package_matches_search(package, search)]

    return {
        "success": True,
        "total": len(enriched_packages),
        "data": serialize_list(enriched_packages),
    }


@router.get("/summary")
async def get_package_summary(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get package dashboard counters for the management page."""

    await sync_expired_packages(db)
    dt = now_local()
    expiring_deadline = dt + timedelta(days=EXPIRING_SOON_DAYS)

    active = await db.packages.count_documents(
        {"status": "active", "package_type": {"$in": STORED_PACKAGE_TYPES}, "expire_date": {"$gt": dt}}
    )
    expiring_soon = await db.packages.count_documents(
        {
            "status": "active",
            "package_type": {"$in": STORED_PACKAGE_TYPES},
            "expire_date": {"$gt": dt, "$lte": expiring_deadline},
        }
    )
    expired = await db.packages.count_documents({"status": "expired"})
    cancelled = await db.packages.count_documents({"status": "cancelled"})

    transactions = await db.transactions.find({"transaction_type": {"$in": ["package_purchase", "package_renewal"]}}).to_list(length=10000)
    package_revenue = sum(float(transaction.get("amount") or 0) for transaction in transactions)

    return {
        "success": True,
        "data": {
            "active": active,
            "expiring_soon": expiring_soon,
            "expired": expired,
            "cancelled": cancelled,
            "package_revenue": package_revenue,
        },
    }


@router.post("")
async def create_package(package: PackageCreate, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Create a daily/monthly package for a customer's active vehicle."""

    await sync_expired_packages(db)

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
            "expire_date": {"$gt": now_local()},
        }
    )
    if active_existing:
        raise HTTPException(status_code=400, detail="Vehicle already has an active package")

    package_id = await generate_id(db, "packages", "P")

    price = FeeCalculator.get_package_price(package.package_type)
    start_date = now_local()
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
        "updated_at": start_date,
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
            "vehicle_id": package.vehicle_id,
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


@router.get("/{package_id}")
async def get_package_detail(package_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get package detail with customer and vehicle info."""

    await sync_expired_packages(db)
    package = await db.packages.find_one({"package_id": package_id})
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    enriched = await enrich_packages(db, [package])
    return {
        "success": True,
        "data": enriched[0] if enriched else serialize_mongodb_document(package),
    }


@router.post("/{package_id}/renew")
async def renew_package(
    package_id: str,
    payload: PackageRenewRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Renew an existing daily/monthly package for the same vehicle."""

    await sync_expired_packages(db)
    existing = await db.packages.find_one({"package_id": package_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Package not found")
    if existing.get("status") == "cancelled":
        raise HTTPException(status_code=400, detail="Cancelled package cannot be renewed")

    try:
        package_type = payload.package_type or PackageType(existing.get("package_type"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Existing package type is invalid") from exc
    if package_type == PackageType.PER_USE:
        raise HTTPException(status_code=400, detail="per_use is a billing mode, not a stored package")

    customer = await db.customers.find_one({"customer_id": existing.get("customer_id"), "is_active": True})
    vehicle = await db.vehicles.find_one(
        {
            "vehicle_id": existing.get("vehicle_id"),
            "customer_id": existing.get("customer_id"),
            "is_active": True,
        }
    )
    if not customer or not vehicle:
        raise HTTPException(status_code=400, detail="Customer and vehicle must still be active to renew package")

    dt = now_local()
    current_expire = existing.get("expire_date")
    start_for_extend = current_expire if current_expire and current_expire > dt else dt
    new_expire_date = Package.calculate_expire_date(package_type, start_for_extend)
    price = FeeCalculator.get_package_price(package_type)

    await db.packages.update_one(
        {"package_id": package_id},
        {
            "$set": {
                "package_type": package_type.value,
                "price": price,
                "expire_date": new_expire_date,
                "status": "active",
                "updated_at": dt,
                "last_renewed_at": dt,
            },
            "$inc": {"renewal_count": 1},
        },
    )

    transaction_id = await generate_id(db, "transactions", "T")
    await db.transactions.insert_one(
        {
            "transaction_id": transaction_id,
            "customer_id": existing.get("customer_id"),
            "transaction_type": "package_renewal",
            "amount": price,
            "package_id": package_id,
            "vehicle_id": existing.get("vehicle_id"),
            "payment_method": "cash",
            "description": f"Package renewal - {package_type.value}",
            "created_at": dt,
        }
    )

    updated = await db.packages.find_one({"package_id": package_id})
    enriched = await enrich_packages(db, [updated])
    return {
        "success": True,
        "message": "Package renewed successfully",
        "transaction_id": transaction_id,
        "data": enriched[0],
    }


@router.post("/{package_id}/cancel")
async def cancel_package(package_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Cancel an active package when the vehicle is not currently parked."""

    await sync_expired_packages(db)
    existing = await db.packages.find_one({"package_id": package_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Package not found")
    if existing.get("status") == "cancelled":
        return {"success": True, "message": "Package already cancelled"}

    active_session = await db.sessions.find_one(
        {
            "vehicle_id": existing.get("vehicle_id"),
            "status": "in_progress",
        }
    )
    if active_session:
        raise HTTPException(status_code=400, detail="Cannot cancel package while vehicle is currently parked")

    dt = now_local()
    await db.packages.update_one(
        {"package_id": package_id},
        {
            "$set": {
                "status": "cancelled",
                "cancelled_at": dt,
                "updated_at": dt,
            }
        },
    )

    return {
        "success": True,
        "message": "Package cancelled successfully",
    }
