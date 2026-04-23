"""
RFID Controller - Main endpoint for ESP32
"""
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import logging

from app.database import get_database
from app.utils.id_generator import generate_id
from app.utils.serializers import serialize_mongodb_document
from app.services.fee_calculator import FeeCalculator
from app.models.customer import CustomerType
from app.models.session import SessionStatus
from app.models.parking_slot import SlotStatus

logger = logging.getLogger(__name__)

router = APIRouter()


class RFIDScanRequest(BaseModel):
    """RFID Scan request from ESP32"""
    card_uid: str = Field(..., description="Card UID")
    gate_id: int = Field(1, description="Gate ID")
    distance_cm: Optional[float] = Field(None, description="Distance from ultrasonic sensor")
    timestamp: Optional[float] = Field(None, description="Timestamp from device (currently ignored; server time is authoritative)")


@router.get("/latest-scan")
async def get_latest_scan(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Get latest scanned card UID (for web registration)
    Returns the most recent card UID that was scanned
    """
    # Find the most recent pending card scan
    latest = await db.pending_scans.find_one(
        {},
        sort=[("scanned_at", -1)]
    )
    
    if latest:
        return {
            "success": True,
            "card_uid": latest["card_uid"],
            "scanned_at": latest["scanned_at"].isoformat(),
            "gate_id": latest.get("gate_id", 1)
        }
    else:
        return {
            "success": False,
            "message": "Chưa có thẻ nào được quét. Vui lòng quét thẻ RFID."
        }


@router.delete("/latest-scan")
async def clear_latest_scan(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Clear the latest scan (after registration)"""
    result = await db.pending_scans.delete_many({})
    return {
        "success": True,
        "deleted_count": result.deleted_count
    }


@router.post("/register-card")
async def register_card(
    card_data: dict,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Register a new RFID card"""
    from datetime import datetime
    
    card_uid = card_data.get("card_uid")
    customer_id = card_data.get("customer_id")
    vehicle_id = card_data.get("vehicle_id")
    status = card_data.get("status", "active")
    
    # Check if card already exists
    existing = await db.rfid_cards.find_one({"card_uid": card_uid})
    if existing:
        return {
            "success": False,
            "error": "Thẻ này đã được đăng ký"
        }
    
    # Create card
    card_doc = {
        "card_uid": card_uid,
        "customer_id": customer_id,
        "vehicle_id": vehicle_id,
        "status": status,
        "issued_at": datetime.now(),
        "expire_at": None,
        "created_at": datetime.now(),
        "notes": "Đăng ký từ web"
    }
    
    await db.rfid_cards.insert_one(card_doc)
    
    return {
        "success": True,
        "message": "Đăng ký thẻ thành công",
        "data": serialize_mongodb_document(card_doc)
    }


@router.post("/scan")
async def rfid_scan(request: RFIDScanRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Main RFID scan endpoint
    
    Logic:
    1. Check if card exists
    2. If new card -> Auto register customer, vehicle, card
    3. If existing card:
       - Check for active session
       - If has session -> CHECK-OUT (calculate fee)
       - If no session -> CHECK-IN (create session, assign slot)
    """
    logger.info(f"🔍 RFID SCAN: {request.card_uid}")
    
    card_uid = request.card_uid
    gate_id = request.gate_id
    distance = request.distance_cm
    dt = datetime.now()
    
    # Save to pending scans (for web registration)
    await db.pending_scans.insert_one({
        "card_uid": card_uid,
        "gate_id": gate_id,
        "distance_cm": distance,
        "scanned_at": dt
    })
    
    # Check if card exists
    card = await db.rfid_cards.find_one({"card_uid": card_uid})
    
    if card:
        # EXISTING CARD
        logger.info(f"✅ Existing card: {card_uid}")
        
        # Check card status
        if card["status"] != "active":
            logger.warning(f"⚠️ Card inactive: {card['status']}")
            return {
                "success": False,
                "action": "denied",
                "message": f"Thẻ {card['status']}. Vui lòng liên hệ quản lý.",
                "card_status": card["status"]
            }
        
        customer = await db.customers.find_one({"customer_id": card["customer_id"]})
        vehicle = await db.vehicles.find_one({"vehicle_id": card["vehicle_id"]})

        if not customer or not vehicle:
            logger.warning(f"⚠️ Card data inconsistent for {card_uid}: customer={bool(customer)}, vehicle={bool(vehicle)}")
            return {
                "success": False,
                "action": "denied",
                "message": "Thẻ đang liên kết với dữ liệu không hợp lệ. Vui lòng đăng ký lại hoặc liên hệ quản lý.",
                "error_code": "INCONSISTENT_CARD_BINDING"
            }
        
        # Find active session
        active_session = await db.sessions.find_one({
            "card_uid": card_uid,
            "status": SessionStatus.IN_PROGRESS.value
        })
        
        if active_session:
            # CHECK-OUT - Vehicle exit
            logger.info(f"🚪 CHECK-OUT: {customer['name']}")
            
            # Update session
            exit_time = dt
            entry_time = active_session["entry_time"]
            
            # Check if customer has active package
            active_package = await db.packages.find_one({
                "customer_id": card["customer_id"],
                "status": "active",
                "expire_date": {"$gt": dt}
            })
            
            # Calculate fee
            if active_package:
                parking_fee = 0.0
                package_type = active_package["package_type"]
            else:
                parking_fee = FeeCalculator.calculate_parking_fee(entry_time, exit_time)
                package_type = None
            
            # Update session
            await db.sessions.update_one(
                {"session_id": active_session["session_id"]},
                {
                    "$set": {
                        "exit_time": exit_time,
                        "exit_gate_id": gate_id,
                        "status": SessionStatus.COMPLETED.value,
                        "parking_fee": parking_fee
                    }
                }
            )
            
            # Release parking slot
            if active_session.get("slot_id"):
                await db.parking_slots.update_one(
                    {"slot_id": active_session["slot_id"]},
                    {
                        "$set": {
                            "status": SlotStatus.AVAILABLE.value,
                            "vehicle_id": None,
                            "session_id": None,
                            "updated_at": dt
                        }
                    }
                )
            
            # Create transaction if fee > 0
            if parking_fee > 0:
                transaction_id = await generate_id(db, "transactions", "T")
                await db.transactions.insert_one({
                    "transaction_id": transaction_id,
                    "customer_id": card["customer_id"],
                    "transaction_type": "parking_fee",
                    "amount": parking_fee,
                    "session_id": active_session["session_id"],
                    "payment_method": "cash",
                    "description": f"Phí đỗ xe - {active_session['session_id']}",
                    "created_at": dt
                })
            
            duration_minutes = round((exit_time - entry_time).total_seconds() / 60)
            
            return {
                "success": True,
                "action": "exit",
                "message": "Tạm biệt! Hẹn gặp lại.",
                "customer_name": customer["name"],
                "vehicle_plate": vehicle["plate_number"],
                "session_id": active_session["session_id"],
                "entry_time": entry_time.isoformat(),
                "exit_time": exit_time.isoformat(),
                "parking_fee": parking_fee,
                "duration_minutes": duration_minutes,
                "package_type": package_type
            }
        
        else:
            # CHECK-IN - Vehicle entry
            logger.info(f"🚪 CHECK-IN: {customer['name']}")
            
            # Find available slot
            available_slot = await db.parking_slots.find_one({"status": SlotStatus.AVAILABLE.value})
            
            if not available_slot:
                logger.warning("⚠️ No available slots")
                return {
                    "success": False,
                    "action": "denied",
                    "message": "Bãi đỗ xe đã đầy. Vui lòng quay lại sau.",
                }
            
            # Create session
            session_id = await generate_id(db, "sessions", "S")
            
            session = {
                "session_id": session_id,
                "card_uid": card_uid,
                "customer_id": card["customer_id"],
                "vehicle_id": card["vehicle_id"],
                "slot_id": available_slot["slot_id"],
                "entry_gate_id": gate_id,
                "exit_gate_id": None,
                "entry_time": dt,
                "exit_time": None,
                "distance_cm": distance,
                "status": SessionStatus.IN_PROGRESS.value,
                "parking_fee": 0.0,
                "created_at": dt
            }
            
            await db.sessions.insert_one(session)
            
            # Occupy slot
            await db.parking_slots.update_one(
                {"slot_id": available_slot["slot_id"]},
                {
                    "$set": {
                        "status": SlotStatus.OCCUPIED.value,
                        "vehicle_id": card["vehicle_id"],
                        "session_id": session_id,
                        "updated_at": dt
                    }
                }
            )
            
            return {
                "success": True,
                "action": "entry",
                "message": "Chào mừng quay lại!",
                "customer_name": customer["name"],
                "customer_type": customer.get("customer_type", "walk_in"),
                "vehicle_plate": vehicle["plate_number"],
                "session_id": session_id,
                "slot_id": available_slot["slot_id"]
            }
    
    else:
        # NEW CARD - Auto registration
        logger.info(f"🆕 NEW CARD - Auto registration: {card_uid}")
        
        # Generate IDs
        customer_id = await generate_id(db, "customers", "C")
        vehicle_id = await generate_id(db, "vehicles", "V")

        # Find available slot before creating new records
        available_slot = await db.parking_slots.find_one({"status": SlotStatus.AVAILABLE.value})

        if not available_slot:
            return {
                "success": False,
                "action": "denied",
                "message": "Bãi đỗ xe đã đầy.",
            }
        
        # Create customer
        customer = {
            "customer_id": customer_id,
            "name": f"Khách hàng {customer_id}",
            "phone": None,
            "email": None,
            "address": None,
            "id_card": None,
            "customer_type": CustomerType.WALK_IN.value,
            "balance": 0.0,
            "created_at": dt,
            "updated_at": dt,
            "is_active": True,
            "notes": "Tự động tạo khi quét thẻ mới"
        }
        await db.customers.insert_one(customer)
        
        # Create vehicle
        vehicle = {
            "vehicle_id": vehicle_id,
            "customer_id": customer_id,
            "plate_number": f"XX-{vehicle_id[-4:]}",
            "vehicle_type": "motorbike",
            "brand": None,
            "model": None,
            "color": None,
            "created_at": dt,
            "updated_at": dt,
            "is_active": True
        }
        await db.vehicles.insert_one(vehicle)
        
        # Create RFID card
        card_doc = {
            "card_uid": card_uid,
            "customer_id": customer_id,
            "vehicle_id": vehicle_id,
            "status": "active",
            "issued_at": dt,
            "expire_at": None,
            "created_at": dt,
            "notes": "Tự động tạo"
        }
        await db.rfid_cards.insert_one(card_doc)
        
        # Create first session
        session_id = await generate_id(db, "sessions", "S")
        
        session = {
            "session_id": session_id,
            "card_uid": card_uid,
            "customer_id": customer_id,
            "vehicle_id": vehicle_id,
            "slot_id": available_slot["slot_id"],
            "entry_gate_id": gate_id,
            "exit_gate_id": None,
            "entry_time": dt,
            "exit_time": None,
            "distance_cm": distance,
            "status": SessionStatus.IN_PROGRESS.value,
            "parking_fee": 0.0,
            "created_at": dt
        }
        
        await db.sessions.insert_one(session)
        
        # Occupy slot
        await db.parking_slots.update_one(
            {"slot_id": available_slot["slot_id"]},
            {
                "$set": {
                    "status": SlotStatus.OCCUPIED.value,
                    "vehicle_id": vehicle_id,
                    "session_id": session_id,
                    "updated_at": dt
                }
            }
        )
        
        logger.info(f"✅ Created: {customer_id}, {vehicle_id}, {card_uid}")
        
        return {
            "success": True,
            "action": "new_registration",
            "message": "Thẻ mới - Đã tự động đăng ký!",
            "customer_name": customer["name"],
            "customer_id": customer_id,
            "vehicle_plate": vehicle["plate_number"],
            "vehicle_id": vehicle_id,
            "card_uid": card_uid,
            "session_id": session_id,
            "slot_id": available_slot["slot_id"]
        }
