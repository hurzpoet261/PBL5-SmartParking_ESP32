"""
Customer Controller
"""
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.utils.id_generator import generate_id
from app.utils.serializers import serialize_mongodb_document, serialize_list
from app.utils.timezone import now_local
from app.models.customer import CustomerCreate, CustomerUpdate, CustomerType

router = APIRouter()

PHONE_RE = re.compile(r"^\d{1,10}$")


def normalize_optional_text(value: object) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def normalize_phone(value: object) -> Optional[str]:
    phone = normalize_optional_text(value)
    if not phone:
        return None
    if not PHONE_RE.match(phone):
        raise HTTPException(status_code=400, detail="Phone number must contain digits only and be at most 10 characters")
    return phone


def normalize_email(value: object) -> Optional[str]:
    email = normalize_optional_text(value)
    return email.lower() if email else None


async def ensure_unique_customer_fields(
    db: AsyncIOMotorDatabase,
    *,
    phone: Optional[str],
    email: Optional[str],
    id_card: Optional[str],
    exclude_customer_id: Optional[str] = None,
) -> None:
    exclude_filter = {"customer_id": {"$ne": exclude_customer_id}} if exclude_customer_id else {}

    if phone:
        existing = await db.customers.find_one({**exclude_filter, "phone": phone})
        if existing:
            raise HTTPException(status_code=400, detail="Phone number already exists")

    if email:
        existing = await db.customers.find_one(
            {
                **exclude_filter,
                "email": {
                    "$regex": f"^{re.escape(email)}$",
                    "$options": "i",
                },
            }
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")

    if id_card:
        existing = await db.customers.find_one({**exclude_filter, "id_card": id_card})
        if existing:
            raise HTTPException(status_code=400, detail="ID card already exists")


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

    enriched_customers = []
    for customer in customers:
        vehicle_count = await db.vehicles.count_documents({"customer_id": customer.get("customer_id")})
        enriched_customers.append({
            **serialize_mongodb_document(customer),
            "vehicle_count": vehicle_count
        })
    
    return {
        "success": True,
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": serialize_list(enriched_customers)
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
        "package_type": {"$in": ["daily", "monthly"]},
        "expire_date": {"$gt": now_local()}
    })
    
    # Calculate total spent
    transactions = await db.transactions.find({"customer_id": customer_id}).to_list(length=1000)
    total_spent = sum(t["amount"] for t in transactions if t["transaction_type"] == "parking_fee")
    
    return {
        "success": True,
        "data": {
            **serialize_mongodb_document(customer),
            "vehicles": serialize_list(vehicles),
            "rfid_cards": serialize_list(cards),
            "total_sessions": len(sessions),
            "active_sessions": len(active_sessions),
            "total_spent": total_spent,
            "current_package": serialize_mongodb_document(active_package) if active_package else None
        }
    }


@router.post("")
async def create_customer(customer: CustomerCreate, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Create new customer"""
    phone = normalize_phone(customer.phone)
    email = normalize_email(customer.email)
    id_card = normalize_optional_text(customer.id_card)
    await ensure_unique_customer_fields(db, phone=phone, email=email, id_card=id_card)

    customer_id = await generate_id(db, "customers", "C")
    
    dt = now_local()
    new_customer = {
        "customer_id": customer_id,
        "name": customer.name.strip(),
        "phone": phone,
        "email": email,
        "address": normalize_optional_text(customer.address),
        "id_card": id_card,
        "customer_type": customer.customer_type.value,
        "balance": 0.0,
        "created_at": dt,
        "updated_at": dt,
        "is_active": True,
        "notes": normalize_optional_text(customer.notes)
    }
    
    await db.customers.insert_one(new_customer)
    
    return {
        "success": True,
        "message": "Customer created successfully",
        "data": serialize_mongodb_document(new_customer)
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
    
    update_data = customer.model_dump(exclude_unset=True)

    phone = normalize_phone(update_data.get("phone")) if "phone" in update_data else existing.get("phone")
    email = normalize_email(update_data.get("email")) if "email" in update_data else existing.get("email")
    id_card = normalize_optional_text(update_data.get("id_card")) if "id_card" in update_data else existing.get("id_card")
    await ensure_unique_customer_fields(
        db,
        phone=phone,
        email=email,
        id_card=id_card,
        exclude_customer_id=customer_id,
    )

    if "name" in update_data and update_data["name"] is not None:
        update_data["name"] = str(update_data["name"]).strip()
    if "phone" in update_data:
        update_data["phone"] = phone
    if "email" in update_data:
        update_data["email"] = email
    if "address" in update_data:
        update_data["address"] = normalize_optional_text(update_data["address"])
    if "id_card" in update_data:
        update_data["id_card"] = id_card
    if "notes" in update_data:
        update_data["notes"] = normalize_optional_text(update_data["notes"])
    if update_data.get("customer_type") is not None:
        update_data["customer_type"] = update_data["customer_type"].value
    update_data["updated_at"] = now_local()
    
    await db.customers.update_one(
        {"customer_id": customer_id},
        {"$set": update_data}
    )
    
    updated = await db.customers.find_one({"customer_id": customer_id})
    
    return {
        "success": True,
        "message": "Customer updated successfully",
        "data": serialize_mongodb_document(updated)
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

    await db.vehicles.delete_many({"customer_id": customer_id})
    await db.rfid_cards.delete_many({"customer_id": customer_id})
    await db.packages.delete_many({"customer_id": customer_id})
    await db.transactions.delete_many({"customer_id": customer_id})
    await db.parking_slots.update_many(
        {"reserved_customer_id": customer_id, "session_id": None},
        {
            "$set": {
                "status": "available",
                "vehicle_id": None,
                "session_id": None,
                "updated_at": now_local(),
            },
            "$unset": {
                "reserved_customer_id": "",
                "reserved_vehicle_id": "",
                "reserved_package_id": "",
                "reserved_at": "",
            },
        },
    )
    
    return {
        "success": True,
        "message": "Customer deleted successfully"
    }
