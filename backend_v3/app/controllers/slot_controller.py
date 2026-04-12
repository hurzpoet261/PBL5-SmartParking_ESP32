"""
Parking Slot Controller
"""
from shapely.geometry import Polygon, box
from fastapi import APIRouter, Depends, Query, Body
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
from datetime import datetime

from app.database import get_database
from app.config import settings

router = APIRouter()


@router.get("")
async def get_slots(
    status: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all parking slots"""
    query = {}
    
    if status:
        query["status"] = status
    
    slots = await db.parking_slots.find(query).sort([("row", 1), ("col", 1)]).to_list(length=1000)
    
    # 👈 BỔ SUNG VÒNG LẶP NÀY ĐỂ ÉP KIỂU
    for slot in slots:
        slot["_id"] = str(slot["_id"])
    
    return {
        "success": True,
        "total": len(slots),
        "data": slots
    }


@router.get("/map")
async def get_parking_map(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get parking map layout"""
    slots = await db.parking_slots.find().sort([("row", 1), ("col", 1)]).to_list(length=1000)
    
    # Group by row
    map_data = {}
    for slot in slots:
        slot["_id"] = str(slot["_id"])  # 👈 BỔ SUNG DÒNG NÀY ĐỂ FIX LỖI
        
        row = slot["row"]
        if row not in map_data:
            map_data[row] = []
            
        map_data[row].append(slot)
    
    # Get statistics
    total_slots = len(slots)
    available = len([s for s in slots if s["status"] == "available"])
    occupied = len([s for s in slots if s["status"] == "occupied"])
    reserved = len([s for s in slots if s["status"] == "reserved"])
    maintenance = len([s for s in slots if s["status"] == "maintenance"])
    
    return {
        "success": True,
        "rows": settings.PARKING_ROWS,
        "cols": settings.PARKING_COLS,
        "total_slots": total_slots,
        "statistics": {
            "available": available,
            "occupied": occupied,
            "reserved": reserved,
            "maintenance": maintenance,
            "occupancy_rate": round((occupied / total_slots * 100), 1) if total_slots > 0 else 0
        },
        "map": map_data
    }


@router.post("/initialize")
async def initialize_slots(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Initialize parking slots (run once)"""
    # Check if already initialized
    count = await db.parking_slots.count_documents({})
    if count > 0:
        return {
            "success": False,
            "message": "Slots already initialized"
        }
    
    # Create slots
    slots = []
    for row in range(1, settings.PARKING_ROWS + 1):
        for col in range(1, settings.PARKING_COLS + 1):
            slot_id = f"{chr(64 + row)}{col:02d}"  # A01, A02, ..., B01, B02, ...
            slots.append({
                "slot_id": slot_id,
                "row": row,
                "col": col,
                "status": "available",
                "vehicle_id": None,
                "session_id": None,
                "slot_type": "standard",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })
    
    await db.parking_slots.insert_many(slots)
    
    return {
        "success": True,
        "message": f"Initialized {len(slots)} parking slots",
        "total": len(slots)
    }
@router.post("/generate-layout")
async def generate_layout(
    data: dict = Body(...), 
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    scale = data['scale_factor']
    
    # 1. Tạo đa giác ranh giới và vật cản (quy đổi pixel -> mét)
    boundary_coords = [(p['x'] * scale, p['y'] * scale) for p in data['boundary']]
    boundary_poly = Polygon(boundary_coords)
    
    obstacles = []
    for obs_points in data['obstacles']:
        obs_coords = [(p['x'] * scale, p['y'] * scale) for p in obs_points]
        obstacles.append(Polygon(obs_coords))

    # 2. Thuật toán "Lấp đầy" (Grid Filling)
    new_slots = []
    minx, miny, maxx, maxy = boundary_poly.bounds
    
    slot_w, slot_l = 2.5, 5.0 # Kích thước mét
    
    curr_x = minx
    while curr_x < maxx:
        curr_y = miny
        while curr_y < maxy:
            # Tạo ô đỗ xe giả định
            candidate = box(curr_x, curr_y, curr_x + slot_w, curr_y + slot_l)
            
            # Kiểm tra: Nằm trong ranh giới AND không đè vật cản
            is_valid = candidate.within(boundary_poly)
            for obs in obstacles:
                if candidate.intersects(obs):
                    is_valid = False
                    break
            
            if is_valid:
                new_slots.append({
                    "slot_id": f"P-{len(new_slots)+1:03d}",
                    "slot_number": f"A{len(new_slots)+1:03d}",
                    "row": int((curr_y - miny) / slot_l),
                    "col": int((curr_x - minx) / slot_w),
                    "status": "available",
                    "created_at": datetime.now()
                })
            curr_y += slot_l + 0.5 # Khoảng cách giữa các ô
        curr_x += slot_w + 0.5

    # 3. Lưu vào Database (Xóa cũ thay mới)
    if new_slots:
        await db.parking_slots.delete_many({})
        await db.parking_slots.insert_many(new_slots)

    return {"success": True, "total": len(new_slots)}