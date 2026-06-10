"""
Parking Slot Controller
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from app.database import get_database
from app.config import settings
from app.services.layout_optimizer import LayoutConfig, LayoutValidationError, optimize_parking_layout
from app.services.parking_status import publish_parking_status_update
from app.utils.serializers import serialize_mongodb_document, serialize_list
from app.utils.timezone import now_local

router = APIRouter()

SLOT_TYPE_DEFAULTS = {
    "car": {"slot_width": 2.5, "slot_length": 5.0, "aisle_width": 6.0},
    "motorbike": {"slot_width": 1.0, "slot_length": 2.0, "aisle_width": 2.5},
}


class LayoutPoint(BaseModel):
    x: float
    y: float


class LayoutConfigPayload(BaseModel):
    slot_type: str = "car"
    slot_width: Optional[float] = None
    slot_length: Optional[float] = None
    aisle_width: Optional[float] = None
    boundary_margin: float = 0.3
    obstacle_margin: float = 0.3
    angles: List[float] = Field(default_factory=lambda: [0, 15, 30, 45, 60, 75, 90])


class GenerateLayoutRequest(BaseModel):
    scale_factor: float = Field(..., gt=0)
    boundary: List[LayoutPoint]
    obstacles: List[List[LayoutPoint]] = Field(default_factory=list)
    parking_lot_id: str = "LOT1"
    area_id: str = "MAIN"
    config: LayoutConfigPayload = Field(default_factory=LayoutConfigPayload)


class ConfirmLayoutRequest(BaseModel):
    parking_lot_id: str = "LOT1"
    area_id: str = "MAIN"
    replace_existing: bool = True
    generated_slots: List[Dict[str, Any]]
    boundary: List[LayoutPoint] = Field(default_factory=list)
    obstacles: List[List[LayoutPoint]] = Field(default_factory=list)
    scale_factor: Optional[float] = Field(default=None, gt=0)
    canvas_width_px: Optional[float] = Field(default=None, gt=0)
    canvas_height_px: Optional[float] = Field(default=None, gt=0)


def dump_points(points: List[LayoutPoint]) -> List[Dict[str, float]]:
    return [point.model_dump() for point in points]


def dump_obstacles(obstacles: List[List[LayoutPoint]]) -> List[List[Dict[str, float]]]:
    return [dump_points(obstacle) for obstacle in obstacles]


def slot_has_reservation(slot: Dict[str, Any]) -> bool:
    return bool(slot.get("reserved_vehicle_id") or slot.get("reserved_customer_id"))


async def enrich_slot_reservations(
    db: AsyncIOMotorDatabase,
    slots: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    customer_ids = sorted({slot.get("reserved_customer_id") for slot in slots if slot.get("reserved_customer_id")})
    vehicle_ids = sorted({slot.get("reserved_vehicle_id") for slot in slots if slot.get("reserved_vehicle_id")})

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

    enriched = []
    for slot in slots:
        serialized = serialize_mongodb_document(slot)
        serialized["slot_number"] = serialized.get("slot_number") or serialized.get("slot_id")

        reserved_customer = customers_by_id.get(slot.get("reserved_customer_id"))
        reserved_vehicle = vehicles_by_id.get(slot.get("reserved_vehicle_id"))
        serialized["is_fixed_slot"] = slot_has_reservation(slot)
        serialized["reserved_customer_name"] = reserved_customer.get("name") if reserved_customer else None
        serialized["reserved_customer_phone"] = reserved_customer.get("phone") if reserved_customer else None
        serialized["reserved_plate_number"] = reserved_vehicle.get("plate_number") if reserved_vehicle else None
        serialized["reserved_vehicle_type"] = reserved_vehicle.get("vehicle_type") if reserved_vehicle else None
        enriched.append(serialized)

    return enriched


def build_layout_config(payload: GenerateLayoutRequest) -> LayoutConfig:
    slot_type = (payload.config.slot_type or "car").strip().lower()
    defaults = SLOT_TYPE_DEFAULTS.get(slot_type, SLOT_TYPE_DEFAULTS["car"])

    return LayoutConfig(
        slot_type=slot_type,
        slot_width_m=payload.config.slot_width or defaults["slot_width"],
        slot_length_m=payload.config.slot_length or defaults["slot_length"],
        aisle_width_m=payload.config.aisle_width if payload.config.aisle_width is not None else defaults["aisle_width"],
        boundary_margin_m=payload.config.boundary_margin,
        obstacle_margin_m=payload.config.obstacle_margin,
        angles=payload.config.angles,
        parking_lot_id=(payload.parking_lot_id or "LOT1").strip().upper(),
        area_id=(payload.area_id or "MAIN").strip().upper(),
    )


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

    normalized_slots = await enrich_slot_reservations(db, slots)

    return {
        "success": True,
        "total": len(normalized_slots),
        "data": normalized_slots
    }


@router.get("/map")
async def get_parking_map(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get parking map layout"""
    slots = await db.parking_slots.find().sort([("row", 1), ("col", 1)]).to_list(length=1000)

    serialized_slots = await enrich_slot_reservations(db, slots)
    map_data = {}
    for slot, serialized in zip(slots, serialized_slots):
        row = slot.get("row")
        if row is not None:
            if row not in map_data:
                map_data[row] = []
            map_data[row].append(serialized)

    total_slots = len(slots)
    available = len([s for s in slots if s.get("status") == "available" and not slot_has_reservation(s)])
    occupied = len([s for s in slots if s.get("status") == "occupied"])
    reserved = len([s for s in slots if s.get("status") == "reserved" or (s.get("status") == "available" and slot_has_reservation(s))])
    maintenance = len([s for s in slots if s.get("status") == "maintenance"])
    parking_lot_id = (slots[0].get("parking_lot_id") if slots else None) or "LOT1"
    area_id = (slots[0].get("area_id") if slots else None) or "MAIN"
    active_layout = await db.parking_layouts.find_one(
        {
            "parking_lot_id": parking_lot_id,
            "area_id": area_id,
            "status": "active",
        },
        sort=[("updated_at", -1)],
    )

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
        "data": serialized_slots,
        "map": map_data,
        "layout": serialize_mongodb_document(active_layout) if active_layout else None,
    }


@router.post("/generate-layout")
async def generate_layout_preview(
    payload: GenerateLayoutRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Generate an optimized parking slot layout for preview only."""
    del db
    try:
        result = optimize_parking_layout(
            boundary=[point.model_dump() for point in payload.boundary],
            obstacles=[[point.model_dump() for point in obstacle] for obstacle in payload.obstacles],
            scale_factor=payload.scale_factor,
            config=build_layout_config(payload),
        )
        result["mode"] = "preview"
        return result
    except LayoutValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/confirm-layout")
async def confirm_layout(
    payload: ConfirmLayoutRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Persist a previously generated layout, without deleting occupied slots."""
    if not payload.generated_slots:
        raise HTTPException(status_code=400, detail="generated_slots is required")

    parking_lot_id = (payload.parking_lot_id or "LOT1").strip().upper()
    area_id = (payload.area_id or "MAIN").strip().upper()
    lot_filter = {
        "$or": [
            {"parking_lot_id": parking_lot_id},
            {"parking_lot_id": {"$exists": False}},
        ]
    }
    existing_count = await db.parking_slots.count_documents(lot_filter)
    if existing_count and not payload.replace_existing:
        raise HTTPException(
            status_code=400,
            detail="Layout already exists. Set replace_existing=true to replace non-occupied slots.",
        )

    protected_filter = {
        "$and": [
            lot_filter,
            {
                "$or": [
                    {"status": "occupied"},
                    {"status": "reserved"},
                    {"session_id": {"$ne": None}},
                    {
                        "$and": [
                            {"reserved_vehicle_id": {"$exists": True}},
                            {"reserved_vehicle_id": {"$ne": None}},
                        ]
                    },
                    {
                        "$and": [
                            {"reserved_customer_id": {"$exists": True}},
                            {"reserved_customer_id": {"$ne": None}},
                        ]
                    },
                ]
            },
        ]
    }
    protected_slots = await db.parking_slots.find(protected_filter).to_list(length=10000)
    protected_ids = {slot.get("slot_id") for slot in protected_slots if slot.get("slot_id")}

    deleted_count = 0
    if payload.replace_existing:
        delete_filter = {
            "$and": [
                lot_filter,
                {"status": {"$nin": ["occupied", "reserved"]}},
                {"session_id": None},
                {
                    "$or": [
                        {"reserved_vehicle_id": None},
                        {"reserved_vehicle_id": {"$exists": False}},
                    ]
                },
                {
                    "$or": [
                        {"reserved_customer_id": None},
                        {"reserved_customer_id": {"$exists": False}},
                    ]
                },
            ]
        }
        delete_result = await db.parking_slots.delete_many(delete_filter)
        deleted_count = delete_result.deleted_count

    dt = now_local()
    layout_metadata = None
    if payload.boundary:
        layout_metadata = {
            "parking_lot_id": parking_lot_id,
            "area_id": area_id,
            "status": "active",
            "boundary_points": dump_points(payload.boundary),
            "obstacle_points": dump_obstacles(payload.obstacles),
            "scale_factor": payload.scale_factor,
            "scale_unit": "meter_per_pixel" if payload.scale_factor else None,
            "canvas_width_px": payload.canvas_width_px,
            "canvas_height_px": payload.canvas_height_px,
            "slot_count": len(payload.generated_slots),
            "updated_at": dt,
            "confirmed_at": dt,
        }

    used_ids = set(protected_ids)
    docs = []
    for index, slot in enumerate(payload.generated_slots, start=1):
        base_code = str(
            slot.get("slot_id")
            or slot.get("slot_number")
            or slot.get("slot_code")
            or f"{parking_lot_id}-G-{index:03d}"
        ).strip().upper()
        slot_id = base_code
        suffix = 1
        while slot_id in used_ids:
            suffix += 1
            slot_id = f"{base_code}-R{suffix}"
        used_ids.add(slot_id)

        doc = {
            "slot_id": slot_id,
            "slot_number": slot_id,
            "slot_code": slot_id,
            "parking_lot_id": parking_lot_id,
            "area_id": area_id,
            "row": int(slot.get("row") or slot.get("row_index", 0) + 1),
            "col": int(slot.get("col") or slot.get("col_index", 0) + 1),
            "status": "available",
            "vehicle_id": None,
            "session_id": None,
            "slot_type": str(slot.get("slot_type") or "car").lower(),
            "x": float(slot.get("x") or 0),
            "y": float(slot.get("y") or 0),
            "width_m": float(slot.get("width_m") or 0),
            "length_m": float(slot.get("length_m") or 0),
            "width_px": float(slot.get("width_px") or 0),
            "height_px": float(slot.get("height_px") or 0),
            "angle": float(slot.get("angle") or 0),
            "points": slot.get("points") or [],
            "created_at": dt,
            "updated_at": dt,
        }
        docs.append(doc)

    if docs:
        await db.parking_slots.insert_many(docs)
    if layout_metadata:
        await db.parking_layouts.update_one(
            {
                "parking_lot_id": parking_lot_id,
                "area_id": area_id,
                "status": "active",
            },
            {
                "$set": layout_metadata,
                "$setOnInsert": {
                    "layout_id": f"{parking_lot_id}-{area_id}-ACTIVE",
                    "created_at": dt,
                },
            },
            upsert=True,
        )
    await publish_parking_status_update(db)

    return {
        "success": True,
        "message": f"Saved {len(docs)} generated slots",
        "saved": len(docs),
        "deleted": deleted_count,
        "preserved_occupied": len([slot for slot in protected_slots if slot.get("status") == "occupied"]),
        "preserved_reserved": len([slot for slot in protected_slots if slot.get("status") == "reserved" or slot.get("reserved_vehicle_id")]),
        "layout_metadata_saved": bool(layout_metadata),
        "layout_metadata": layout_metadata,
        "data": serialize_list(docs),
    }


@router.get("/{slot_id}")
async def get_slot_detail(slot_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get parking slot detail"""
    slot = await db.parking_slots.find_one({"slot_id": slot_id})

    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    slot_data = (await enrich_slot_reservations(db, [slot]))[0]

    if slot.get("session_id"):
        session = await db.sessions.find_one({"session_id": slot["session_id"]})
        if session:
            customer = await db.customers.find_one({"customer_id": session.get("customer_id")})
            vehicle = await db.vehicles.find_one({"vehicle_id": session.get("vehicle_id")})
            slot_data["current_session"] = serialize_mongodb_document({
                "session_id": session.get("session_id"),
                "customer_name": customer.get("name") if customer else "N/A",
                "plate_number": vehicle.get("plate_number") if vehicle else "N/A",
                "check_in_time": session.get("entry_time")
            })
        else:
            slot_data["current_session"] = None
    else:
        slot_data["current_session"] = None

    return {
        "success": True,
        "data": slot_data
    }


@router.post("/initialize")
async def initialize_slots(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Initialize parking slots (run once)"""
    count = await db.parking_slots.count_documents({})
    if count > 0:
        return {
            "success": False,
            "message": "Slots already initialized"
        }

    slots = []
    dt = now_local()
    for row in range(1, settings.PARKING_ROWS + 1):
        for col in range(1, settings.PARKING_COLS + 1):
            slot_id = f"{chr(64 + row)}{col:02d}"
            slots.append({
                "slot_id": slot_id,
                "slot_number": slot_id,
                "row": row,
                "col": col,
                "status": "available",
                "vehicle_id": None,
                "session_id": None,
                "slot_type": "standard",
                "created_at": dt,
                "updated_at": dt
            })

    await db.parking_slots.insert_many(slots)
    await publish_parking_status_update(db)

    return {
        "success": True,
        "message": f"Initialized {len(slots)} parking slots",
        "total": len(slots)
    }
