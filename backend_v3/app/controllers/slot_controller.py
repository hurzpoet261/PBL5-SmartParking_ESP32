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
    # 1. Lấy dữ liệu và kiểm tra
    scale = data.get('scale_factor')
    if not scale:
        return {"success": False, "error": "Thiếu scale_factor"}
        
    boundary_data = data.get('boundary', [])
    if not boundary_data:
        return {"success": False, "error": "Thiếu dữ liệu ranh giới"}

    # Tạo đa giác ranh giới và vật cản (quy đổi pixel -> mét)
    boundary_coords = [(p['x'] * scale, p['y'] * scale) for p in boundary_data]
    boundary_poly = Polygon(boundary_coords)
    
    obstacles = []
    for obs_points in data.get('obstacles', []):
        obs_coords = [(p['x'] * scale, p['y'] * scale) for p in obs_points]
        obstacles.append(Polygon(obs_coords))

    # 2. Thuật toán phân dãy có lối đi (Module 16m)
    new_slots = []
    minx, miny, maxx, maxy = boundary_poly.bounds
    
    slot_w, slot_l = 2.5, 5.0  # Kích thước tiêu chuẩn
    aisle_w = 6.0              # Lối đi
    module_w = (slot_l * 2) + aisle_w # Một cụm 2 dãy + 1 lối đi = 16m
    
    curr_x = minx
    while curr_x + module_w <= maxx:
        # Hàng bên trái
        for y in [val for val in range(int(miny), int(maxy - slot_w), int(slot_w))]:
            candidate = box(curr_x, y, curr_x + slot_l, y + slot_w)
            if candidate.within(boundary_poly) and not any(candidate.intersects(obs) for obs in obstacles):
                new_slots.append({
                    "slot_id": f"P-{len(new_slots)+1:03d}",
                    "slot_number": f"A{len(new_slots)+1:03d}",
                    "row": int((y - miny) / slot_w),
                    "col": int((curr_x - minx) / module_w) * 2,
                    "status": "available",
                    "x_m": curr_x, "y_m": y, # Lưu tọa độ mét
                    "created_at": datetime.now()
                })
        
        # Hàng bên phải (cách 1 lối đi)
        curr_x_right = curr_x + slot_l + aisle_w
        for y in [val for val in range(int(miny), int(maxy - slot_w), int(slot_w))]:
            candidate = box(curr_x_right, y, curr_x_right + slot_l, y + slot_w)
            if candidate.within(boundary_poly) and not any(candidate.intersects(obs) for obs in obstacles):
                new_slots.append({
                    "slot_id": f"P-{len(new_slots)+1:03d}",
                    "slot_number": f"B{len(new_slots)+1:03d}",
                    "row": int((y - miny) / slot_w),
                    "col": int((curr_x - minx) / module_w) * 2 + 1,
                    "status": "available",
                    "x_m": curr_x_right, "y_m": y,
                    "created_at": datetime.now()
                })
        curr_x += module_w + 1.0

    # 3. Lưu vào Database
    if new_slots:
        await db.parking_slots.delete_many({})
        await db.parking_slots.insert_many(new_slots)

    # 4. Trả về dữ liệu Preview cho Frontend vẽ lên Canvas
    preview_slots = []
    for s in new_slots:
        preview_slots.append({
            "slot_number": s["slot_number"],
            "x": s["x_m"] / scale,
            "y": s["y_m"] / scale,
            "width_px": slot_l / scale,
            "height_px": slot_w / scale
        })

    return {
        "success": True, 
        "total": len(new_slots), 
        "generated_slots": preview_slots
    }