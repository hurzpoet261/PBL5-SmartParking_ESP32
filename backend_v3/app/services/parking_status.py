"""
Parking occupancy status publisher for LCD displays.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.gate_mqtt import gate_mqtt_publisher

logger = logging.getLogger(__name__)


async def build_parking_status(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    total = await db.parking_slots.count_documents({})
    available = await db.parking_slots.count_documents({"status": "available"})
    occupied = await db.parking_slots.count_documents({"status": "occupied"})
    reserved = await db.parking_slots.count_documents({"status": "reserved"})
    maintenance = await db.parking_slots.count_documents({"status": "maintenance"})

    return {
        "type": "parking_status",
        "total": total,
        "available": available,
        "occupied": occupied,
        "reserved": reserved,
        "maintenance": maintenance,
        "updated_at": datetime.utcnow().isoformat(),
    }


async def publish_parking_status_update(db: AsyncIOMotorDatabase) -> bool:
    try:
        status = await build_parking_status(db)
        return await asyncio.to_thread(gate_mqtt_publisher.publish_parking_status, status)
    except Exception as exc:
        logger.warning("[PARKING] Failed to publish status: %s", exc)
        return False
