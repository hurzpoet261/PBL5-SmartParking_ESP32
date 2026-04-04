"""
Smart Parking Backend API - Production Ready
Đầy đủ chức năng, logic chặt chẽ, xử lý lỗi tốt
"""

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════

DB_FILE = "parking_database.json"
CORS_ORIGINS = ["*"]  # Trong production nên giới hạn

# ═══════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════

class VehicleType(str, Enum):
    MOTORBIKE = "motorbike"
    CAR = "car"
    BICYCLE = "bicycle"

class CardStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOST = "lost"
    EXPIRED = "expired"

class SessionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class CustomerType(str, Enum):
    WALK_IN = "walk_in"
    MONTHLY = "monthly"
    VIP = "vip"

# ═══════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════

class RFIDScanRequest(BaseModel):
    card_uid: str = Field(..., description="UID của thẻ RFID")
    gate_id: int = Field(1, description="ID cổng")
    distance_cm: Optional[float] = Field(None, description="Khoảng cách từ cảm biến")
    timestamp: Optional[float] = Field(None, description="Timestamp")

class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=200)
    customer_type: CustomerType = CustomerType.WALK_IN

class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=200)
    customer_type: Optional[CustomerType] = None

class VehicleCreate(BaseModel):
    customer_id: str
    plate_number: str = Field(..., min_length=1, max_length=20)
    vehicle_type: VehicleType = VehicleType.MOTORBIKE
    brand: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=30)

class VehicleUpdate(BaseModel):
    plate_number: Optional[str] = Field(None, min_length=1, max_length=20)
    vehicle_type: Optional[VehicleType] = None
    brand: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=30)

# ═══════════════════════════════════════════════════
# DATABASE FUNCTIONS
# ═══════════════════════════════════════════════════

def init_db():
    """Khởi tạo database mới"""
    return {
        "customers": {},
        "vehicles": {},
        "rfid_cards": {},
        "sessions": [],
        "gates": {
            "1": {"gate_id": 1, "name": "Cổng chính", "type": "entry", "status": "active"},
            "2": {"gate_id": 2, "name": "Cổng phụ", "type": "exit", "status": "active"}
        },
        "stats": {
            "total_scans": 0,
            "total_customers": 0,
            "total_vehicles": 0,
            "active_sessions": 0,
            "total_entries": 0,
            "total_exits": 0,
            "today_entries": 0,
            "today_exits": 0,
            "today_revenue": 0.0
        },
        "settings": {
            "parking_fee_per_hour": 5000,  # VNĐ
            "max_capacity": 100,
            "auto_close_gate_seconds": 5
        }
    }

def load_db():
    """Đọc database"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
                logger.info(f"✅ Database loaded: {len(db.get('customers', {}))} customers")
                return db
        except Exception as e:
            logger.error(f"❌ Error loading database: {e}")
            return init_db()
    else:
        logger.info("📝 Creating new database")
        db = init_db()
        save_db(db)
        return db

def save_db(db):
    """Lưu database"""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
        logger.debug(f"💾 Database saved")
    except Exception as e:
        logger.error(f"❌ Error saving database: {e}")
        raise HTTPException(status_code=500, detail="Database save error")

def generate_id(prefix: str, existing_ids: List[str]) -> str:
    """Tạo ID mới"""
    if not existing_ids:
        return f"{prefix}000001"
    
    numbers = [int(id[len(prefix):]) for id in existing_ids if id.startswith(prefix)]
    next_num = max(numbers) + 1 if numbers else 1
    return f"{prefix}{next_num:06d}"

# ═══════════════════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════════════════

app = FastAPI(
    title="Smart Parking API",
    version="2.0.0",
    description="API quản lý bãi đỗ xe thông minh"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"📥 {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"📤 {response.status_code}")
    return response

# ═══════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════

@app.get("/")
def root():
    return {
        "name": "Smart Parking API",
        "version": "2.0.0",
        "status": "online",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "rfid_scan": "POST /api/v1/rfid/scan",
            "customers": "/api/v1/customers",
            "vehicles": "/api/v1/vehicles",
            "sessions": "/api/v1/sessions",
            "stats": "/api/v1/stats"
        }
    }

@app.get("/health")
def health():
    """Health check endpoint"""
    db = load_db()
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "database": {
            "customers": len(db.get("customers", {})),
            "vehicles": len(db.get("vehicles", {})),
            "sessions": len(db.get("sessions", [])),
            "rfid_cards": len(db.get("rfid_cards", {})),
            "active_sessions": db.get("stats", {}).get("active_sessions", 0)
        }
    }

@app.post("/api/v1/rfid/scan")
def rfid_scan(request: RFIDScanRequest):
    """
    Endpoint chính - Xử lý quét thẻ RFID
    Logic: Tự động tạo customer/vehicle nếu thẻ mới, check-in/check-out
    """
    logger.info("=" * 70)
    logger.info(f"🔍 RFID SCAN: {request.card_uid}")
    logger.info("=" * 70)
    
    db = load_db()
    card_uid = request.card_uid
    gate_id = request.gate_id
    distance = request.distance_cm
    timestamp = request.timestamp or datetime.now().timestamp()
    dt = datetime.fromtimestamp(timestamp)
    
    # Update stats
    db["stats"]["total_scans"] += 1
    
    # Kiểm tra thẻ đã tồn tại chưa
    if card_uid in db["rfid_cards"]:
        logger.info(f"✅ Existing card: {card_uid}")
        
        card = db["rfid_cards"][card_uid]
        
        # Kiểm tra trạng thái thẻ
        if card["status"] != "active":
            logger.warning(f"⚠️ Card inactive: {card['status']}")
            return {
                "success": False,
                "action": "denied",
                "message": f"Thẻ {card['status']}. Vui lòng liên hệ quản lý.",
                "card_status": card["status"]
            }
        
        customer = db["customers"].get(card["customer_id"])
        vehicle = db["vehicles"].get(card["vehicle_id"])
        
        # Tìm session đang mở
        active_session = None
        for session in db["sessions"]:
            if session["card_uid"] == card_uid and session["status"] == "in_progress":
                active_session = session
                break
        
        if active_session:
            # CHECK-OUT - Xe ra
            logger.info(f"🚪 CHECK-OUT: {customer['name']}")
            
            active_session["exit_time"] = dt.isoformat()
            active_session["exit_gate_id"] = gate_id
            active_session["status"] = "completed"
            
            # Tính phí (nếu không phải monthly)
            if customer.get("customer_type") != "monthly":
                entry_time = datetime.fromisoformat(active_session["entry_time"])
                duration_hours = (dt - entry_time).total_seconds() / 3600
                fee = max(1, round(duration_hours)) * db["settings"]["parking_fee_per_hour"]
                active_session["parking_fee"] = fee
                db["stats"]["today_revenue"] += fee
            else:
                active_session["parking_fee"] = 0
            
            db["stats"]["active_sessions"] -= 1
            db["stats"]["total_exits"] += 1
            db["stats"]["today_exits"] += 1
            
            save_db(db)
            
            return {
                "success": True,
                "action": "exit",
                "message": "Tạm biệt! Hẹn gặp lại.",
                "customer_name": customer["name"],
                "vehicle_plate": vehicle["plate_number"],
                "session_id": active_session["session_id"],
                "entry_time": active_session["entry_time"],
                "exit_time": active_session["exit_time"],
                "parking_fee": active_session.get("parking_fee", 0),
                "duration_minutes": round((dt - entry_time).total_seconds() / 60)
            }
        else:
            # CHECK-IN - Xe vào
            logger.info(f"🚪 CHECK-IN: {customer['name']}")
            
            # Kiểm tra capacity
            if db["stats"]["active_sessions"] >= db["settings"]["max_capacity"]:
                logger.warning("⚠️ Parking lot full")
                return {
                    "success": False,
                    "action": "denied",
                    "message": "Bãi đỗ xe đã đầy. Vui lòng quay lại sau.",
                    "capacity": db["settings"]["max_capacity"]
                }
            
            session_id = generate_id("S", [s["session_id"] for s in db["sessions"]])
            
            session = {
                "session_id": session_id,
                "card_uid": card_uid,
                "customer_id": card["customer_id"],
                "vehicle_id": card["vehicle_id"],
                "entry_gate_id": gate_id,
                "exit_gate_id": None,
                "entry_time": dt.isoformat(),
                "exit_time": None,
                "distance_cm": distance,
                "status": "in_progress",
                "parking_fee": 0
            }
            
            db["sessions"].append(session)
            db["stats"]["active_sessions"] += 1
            db["stats"]["total_entries"] += 1
            db["stats"]["today_entries"] += 1
            
            save_db(db)
            
            return {
                "success": True,
                "action": "entry",
                "message": "Chào mừng quay lại!",
                "customer_name": customer["name"],
                "customer_type": customer.get("customer_type", "walk_in"),
                "vehicle_plate": vehicle["plate_number"],
                "session_id": session_id
            }
    
    else:
        # THẺ MỚI - Tự động đăng ký
        logger.info(f"🆕 NEW CARD - Auto registration: {card_uid}")
        
        customer_id = generate_id("C", list(db["customers"].keys()))
        vehicle_id = generate_id("V", list(db["vehicles"].keys()))
        
        # Tạo customer
        customer = {
            "customer_id": customer_id,
            "name": f"Khách hàng {customer_id}",
            "phone": None,
            "email": None,
            "address": None,
            "customer_type": "walk_in",
            "created_at": dt.isoformat(),
            "updated_at": dt.isoformat(),
            "card_uid": card_uid
        }
        db["customers"][customer_id] = customer
        db["stats"]["total_customers"] += 1
        
        # Tạo vehicle
        vehicle = {
            "vehicle_id": vehicle_id,
            "customer_id": customer_id,
            "plate_number": f"XX-{vehicle_id[-4:]}",
            "vehicle_type": "motorbike",
            "brand": None,
            "model": None,
            "color": None,
            "created_at": dt.isoformat(),
            "updated_at": dt.isoformat()
        }
        db["vehicles"][vehicle_id] = vehicle
        db["stats"]["total_vehicles"] += 1
        
        # Tạo RFID card
        card = {
            "card_uid": card_uid,
            "card_code": generate_id("CARD-", [c.get("card_code", "") for c in db["rfid_cards"].values()]),
            "customer_id": customer_id,
            "vehicle_id": vehicle_id,
            "status": "active",
            "card_type": "guest",
            "issued_at": dt.isoformat(),
            "created_at": dt.isoformat()
        }
        db["rfid_cards"][card_uid] = card
        
        # Tạo session đầu tiên
        session_id = generate_id("S", [s["session_id"] for s in db["sessions"]])
        
        session = {
            "session_id": session_id,
            "card_uid": card_uid,
            "customer_id": customer_id,
            "vehicle_id": vehicle_id,
            "entry_gate_id": gate_id,
            "exit_gate_id": None,
            "entry_time": dt.isoformat(),
            "exit_time": None,
            "distance_cm": distance,
            "status": "in_progress",
            "parking_fee": 0
        }
        
        db["sessions"].append(session)
        db["stats"]["active_sessions"] += 1
        db["stats"]["total_entries"] += 1
        db["stats"]["today_entries"] += 1
        
        save_db(db)
        
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
            "session_id": session_id
        }

# Tiếp tục trong phần 2...


# ═══════════════════════════════════════════════════
# CUSTOMER ENDPOINTS
# ═══════════════════════════════════════════════════

@app.get("/api/v1/customers")
def get_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    customer_type: Optional[CustomerType] = None
):
    """Lấy danh sách khách hàng"""
    db = load_db()
    customers = list(db["customers"].values())
    
    # Filter by type
    if customer_type:
        customers = [c for c in customers if c.get("customer_type") == customer_type]
    
    # Pagination
    total = len(customers)
    customers = customers[skip:skip + limit]
    
    return {
        "success": True,
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": customers
    }

@app.get("/api/v1/customers/{customer_id}")
def get_customer(customer_id: str):
    """Lấy thông tin 1 khách hàng"""
    db = load_db()
    customer = db["customers"].get(customer_id)
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Lấy thêm thông tin liên quan
    vehicles = [v for v in db["vehicles"].values() if v["customer_id"] == customer_id]
    cards = [c for c in db["rfid_cards"].values() if c["customer_id"] == customer_id]
    sessions = [s for s in db["sessions"] if s["customer_id"] == customer_id]
    
    return {
        "success": True,
        "data": {
            **customer,
            "vehicles": vehicles,
            "rfid_cards": cards,
            "total_sessions": len(sessions),
            "active_sessions": len([s for s in sessions if s["status"] == "in_progress"])
        }
    }

@app.post("/api/v1/customers")
def create_customer(customer: CustomerCreate):
    """Tạo khách hàng mới"""
    db = load_db()
    
    customer_id = generate_id("C", list(db["customers"].keys()))
    
    new_customer = {
        "customer_id": customer_id,
        "name": customer.name,
        "phone": customer.phone,
        "email": customer.email,
        "address": customer.address,
        "customer_type": customer.customer_type,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    db["customers"][customer_id] = new_customer
    db["stats"]["total_customers"] += 1
    save_db(db)
    
    logger.info(f"✅ Created customer: {customer_id}")
    
    return {
        "success": True,
        "message": "Customer created successfully",
        "data": new_customer
    }

@app.put("/api/v1/customers/{customer_id}")
def update_customer(customer_id: str, customer: CustomerUpdate):
    """Cập nhật thông tin khách hàng"""
    db = load_db()
    
    if customer_id not in db["customers"]:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    existing = db["customers"][customer_id]
    
    # Update fields
    if customer.name is not None:
        existing["name"] = customer.name
    if customer.phone is not None:
        existing["phone"] = customer.phone
    if customer.email is not None:
        existing["email"] = customer.email
    if customer.address is not None:
        existing["address"] = customer.address
    if customer.customer_type is not None:
        existing["customer_type"] = customer.customer_type
    
    existing["updated_at"] = datetime.now().isoformat()
    
    save_db(db)
    
    logger.info(f"✅ Updated customer: {customer_id}")
    
    return {
        "success": True,
        "message": "Customer updated successfully",
        "data": existing
    }

@app.delete("/api/v1/customers/{customer_id}")
def delete_customer(customer_id: str):
    """Xóa khách hàng"""
    db = load_db()
    
    if customer_id not in db["customers"]:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Check active sessions
    active_sessions = [s for s in db["sessions"] if s["customer_id"] == customer_id and s["status"] == "in_progress"]
    if active_sessions:
        raise HTTPException(status_code=400, detail="Cannot delete customer with active parking sessions")
    
    del db["customers"][customer_id]
    db["stats"]["total_customers"] -= 1
    save_db(db)
    
    logger.info(f"✅ Deleted customer: {customer_id}")
    
    return {
        "success": True,
        "message": "Customer deleted successfully"
    }

# ═══════════════════════════════════════════════════
# VEHICLE ENDPOINTS
# ═══════════════════════════════════════════════════

@app.get("/api/v1/vehicles")
def get_vehicles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    vehicle_type: Optional[VehicleType] = None
):
    """Lấy danh sách xe"""
    db = load_db()
    vehicles = list(db["vehicles"].values())
    
    if vehicle_type:
        vehicles = [v for v in vehicles if v.get("vehicle_type") == vehicle_type]
    
    total = len(vehicles)
    vehicles = vehicles[skip:skip + limit]
    
    return {
        "success": True,
        "total": total,
        "data": vehicles
    }

@app.put("/api/v1/vehicles/{vehicle_id}")
def update_vehicle(vehicle_id: str, vehicle: VehicleUpdate):
    """Cập nhật thông tin xe"""
    db = load_db()
    
    if vehicle_id not in db["vehicles"]:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    existing = db["vehicles"][vehicle_id]
    
    if vehicle.plate_number is not None:
        existing["plate_number"] = vehicle.plate_number
    if vehicle.vehicle_type is not None:
        existing["vehicle_type"] = vehicle.vehicle_type
    if vehicle.brand is not None:
        existing["brand"] = vehicle.brand
    if vehicle.model is not None:
        existing["model"] = vehicle.model
    if vehicle.color is not None:
        existing["color"] = vehicle.color
    
    existing["updated_at"] = datetime.now().isoformat()
    
    save_db(db)
    
    return {
        "success": True,
        "message": "Vehicle updated successfully",
        "data": existing
    }

# ═══════════════════════════════════════════════════
# SESSION ENDPOINTS
# ═══════════════════════════════════════════════════

@app.get("/api/v1/sessions")
def get_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[SessionStatus] = None
):
    """Lấy danh sách phiên đỗ xe"""
    db = load_db()
    sessions = db["sessions"]
    
    if status:
        sessions = [s for s in sessions if s["status"] == status]
    
    total = len(sessions)
    sessions = sessions[-limit-skip:-skip if skip > 0 else None]
    sessions.reverse()
    
    return {
        "success": True,
        "total": total,
        "data": sessions
    }

@app.get("/api/v1/sessions/{session_id}")
def get_session(session_id: str):
    """Lấy thông tin 1 phiên"""
    db = load_db()
    session = next((s for s in db["sessions"] if s["session_id"] == session_id), None)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Lấy thông tin liên quan
    customer = db["customers"].get(session["customer_id"])
    vehicle = db["vehicles"].get(session["vehicle_id"])
    
    return {
        "success": True,
        "data": {
            **session,
            "customer": customer,
            "vehicle": vehicle
        }
    }

# ═══════════════════════════════════════════════════
# RFID CARD ENDPOINTS
# ═══════════════════════════════════════════════════

@app.get("/api/v1/rfid-cards")
def get_rfid_cards(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[CardStatus] = None
):
    """Lấy danh sách thẻ RFID"""
    db = load_db()
    cards = list(db["rfid_cards"].values())
    
    if status:
        cards = [c for c in cards if c["status"] == status]
    
    total = len(cards)
    cards = cards[skip:skip + limit]
    
    return {
        "success": True,
        "total": total,
        "data": cards
    }

# ═══════════════════════════════════════════════════
# STATS ENDPOINTS
# ═══════════════════════════════════════════════════

@app.get("/api/v1/stats")
def get_stats():
    """Lấy thống kê tổng quan"""
    db = load_db()
    return {
        "success": True,
        "data": db["stats"]
    }

@app.get("/api/v1/stats/dashboard")
def get_dashboard_stats():
    """Lấy thống kê cho dashboard"""
    db = load_db()
    
    # Tính toán thêm
    today = datetime.now().date()
    today_sessions = [s for s in db["sessions"] if datetime.fromisoformat(s["entry_time"]).date() == today]
    
    return {
        "success": True,
        "data": {
            **db["stats"],
            "today_sessions": len(today_sessions),
            "capacity_used_percent": round((db["stats"]["active_sessions"] / db["settings"]["max_capacity"]) * 100, 1),
            "available_slots": db["settings"]["max_capacity"] - db["stats"]["active_sessions"]
        }
    }

# ═══════════════════════════════════════════════════
# TEST ENDPOINTS
# ═══════════════════════════════════════════════════

@app.post("/api/v1/test/scan")
def test_scan(card_uid: str = "TEST001"):
    """Test endpoint - Giả lập quét thẻ"""
    request = RFIDScanRequest(
        card_uid=card_uid,
        gate_id=1,
        distance_cm=25.0
    )
    return rfid_scan(request)

@app.delete("/api/v1/test/reset")
def reset_database():
    """Reset database - CHỈ DÙNG ĐỂ TEST"""
    db = init_db()
    save_db(db)
    logger.warning("⚠️ DATABASE RESET!")
    return {
        "success": True,
        "message": "Database has been reset"
    }

# ═══════════════════════════════════════════════════
# RUN SERVER
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print("  🚗 SMART PARKING BACKEND API v2.0")
    print("=" * 70)
    print(f"  Server:   http://0.0.0.0:8000")
    print(f"  API Docs: http://0.0.0.0:8000/docs")
    print(f"  Health:   http://0.0.0.0:8000/health")
    print("=" * 70)
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
