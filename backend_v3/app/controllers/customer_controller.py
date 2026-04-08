"""
Customer Controller
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List
from datetime import datetime

from app.database import get_database
from app.utils.id_generator import generate_id
from app.models.customer import CustomerCreate, CustomerUpdate, CustomerType

router = APIRouter()


@router.get("")
async def get_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    customer_type: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get list of customers"""
    query = {}
    
    if customer_type:
        query["customer_type"] = customer_type
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    total = await db.customers.count_documents(query)
    customers = await db.customers.find(query).skip(skip).limit(limit).to_list(length=limit)
    
    return {
        "success": True,
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": customers
    }


@router.get("/{customer_id}")
async def get_customer(customer_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get customer details"""
    customer = await db.customers.find_one({"customer_id": customer_id})
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get related data
    vehicles = await db.vehicles.find({"customer_id": customer_id}).to_list(length=100)
    cards = await db.rfid_cards.find({"customer_id": customer_id}).to_list(length=100)
    sessions = await db.sessions.find({"customer_id": customer_id}).to_list(length=100)
    active_sessions = [s for s in sessions if s["status"] == "in_progress"]
    
    # Get active package
    active_package = await db.packages.find_one({
        "customer_id": customer_id,
        "status": "active",
        "expire_date": {"$gt": datetime.now()}
    })
    
    # Calculate total spent
    transactions = await db.transactions.find({"customer_id": customer_id}).to_list(length=1000)
    total_spent = sum(t["amount"] for t in transactions if t["transaction_type"] == "parking_fee")
    
    return {
        "success": True,
        "data": {
            **customer,
            "vehicles": vehicles,
            "rfid_cards": cards,
            "total_sessions": len(sessions),
            "active_sessions": len(active_sessions),
            "total_spent": total_spent,
            "current_package": active_package
        }
    }


@router.post("")
async def create_customer(customer: CustomerCreate, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Create new customer"""
    customer_id = await generate_id(db, "customers", "C")
    
    new_customer = {
        "customer_id": customer_id,
        "name": customer.name,
        "phone": customer.phone,
        "email": customer.email,
        "address": customer.address,
        "id_card": customer.id_card,
        "customer_type": customer.customer_type.value,
        "balance": 0.0,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "is_active": True,
        "notes": customer.notes
    }
    
    await db.customers.insert_one(new_customer)
    
    return {
        "success": True,
        "message": "Customer created successfully",
        "data": new_customer
    }


@router.put("/{customer_id}")
async def update_customer(
    customer_id: str,
    customer: CustomerUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update customer"""
    existing = await db.customers.find_one({"customer_id": customer_id})
    
    if not existing:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    update_data = {k: v for k, v in customer.dict(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = datetime.now()
    
    await db.customers.update_one(
        {"customer_id": customer_id},
        {"$set": update_data}
    )
    
    updated = await db.customers.find_one({"customer_id": customer_id})
    
    return {
        "success": True,
        "message": "Customer updated successfully",
        "data": updated
    }


@router.delete("/{customer_id}")
async def delete_customer(customer_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Delete customer"""
    # Check for active sessions
    active_sessions = await db.sessions.count_documents({
        "customer_id": customer_id,
        "status": "in_progress"
    })
    
    if active_sessions > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete customer with active parking sessions"
        )
    
    result = await db.customers.delete_one({"customer_id": customer_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return {
        "success": True,
        "message": "Customer deleted successfully"
    }
