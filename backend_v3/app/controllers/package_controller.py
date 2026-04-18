"""
Package Controller - Quản lý gói cước
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
from datetime import datetime

from app.database import get_database
from app.utils.id_generator import generate_id
from app.utils.serializers import serialize_mongodb_document, serialize_list
from app.models.package import PackageCreate, Package, PackageType
from app.services.fee_calculator import FeeCalculator

router = APIRouter()


@router.get("")
async def get_packages(
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get list of packages"""
    query = {}
    
    if customer_id:
        query["customer_id"] = customer_id
    
    if status:
        query["status"] = status
    
    packages = await db.packages.find(query).sort("created_at", -1).to_list(length=1000)
    
    return {
        "success": True,
        "total": len(packages),
        "data": serialize_list(packages)
    }


@router.post("")
async def create_package(package: PackageCreate, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Create new package"""
    # Validate customer and vehicle
    customer = await db.customers.find_one({"customer_id": package.customer_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    vehicle = await db.vehicles.find_one({"vehicle_id": package.vehicle_id})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Generate package ID
    package_id = await generate_id(db, "packages", "P")
    
    # Calculate price and expire date
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
        "created_at": start_date
    }
    
    await db.packages.insert_one(new_package)
    
    # Create transaction
    transaction_id = await generate_id(db, "transactions", "T")
    await db.transactions.insert_one({
        "transaction_id": transaction_id,
        "customer_id": package.customer_id,
        "transaction_type": "package_purchase",
        "amount": price,
        "package_id": package_id,
        "payment_method": "cash",
        "description": f"Mua gói {package.package_type.value}",
        "created_at": start_date
    })
    
    return {
        "success": True,
        "message": "Package created successfully",
        "data": serialize_mongodb_document(new_package)
    }


@router.get("/types")
async def get_package_types():
    """Get available package types and prices"""
    from app.config import settings
    
    return {
        "success": True,
        "data": [
            {
                "type": "per_use",
                "name": "Theo lượt",
                "price": settings.FEE_PER_HOUR,
                "unit": "VNĐ/giờ",
                "description": "Tính phí theo giờ đỗ xe"
            },
            {
                "type": "daily",
                "name": "Theo ngày",
                "price": settings.FEE_DAILY_PACKAGE,
                "unit": "VNĐ/ngày",
                "description": "Đỗ xe không giới hạn trong 1 ngày"
            },
            {
                "type": "monthly",
                "name": "Theo tháng",
                "price": settings.FEE_MONTHLY_PACKAGE,
                "unit": "VNĐ/tháng",
                "description": "Đỗ xe không giới hạn trong 30 ngày"
            }
        ]
    }
