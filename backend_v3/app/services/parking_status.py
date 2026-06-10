"""
Parking occupancy status publisher for LCD displays.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.gate_mqtt import gate_mqtt_publisher
from app.utils.timezone import iso_local

logger = logging.getLogger(__name__)


async def build_parking_status(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    total = await db.parking_slots.count_documents({})
    available = await db.parking_slots.count_documents(
        {
            "status": "available",
            "$or": [
                {"reserved_vehicle_id": None},
                {"reserved_vehicle_id": {"$exists": False}},
            ],
            "$and": [
                {
                    "$or": [
                        {"reserved_customer_id": None},
                        {"reserved_customer_id": {"$exists": False}},
                    ]
                }
            ],
        }
    )
    occupied = await db.parking_slots.count_documents({"status": "occupied"})
    reserved = await db.parking_slots.count_documents(
        {
            "$or": [
                {"status": "reserved"},
                {
                    "$and": [
                        {"status": "available"},
                        {
                            "$or": [
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
                },
            ]
        }
    )
    maintenance = await db.parking_slots.count_documents({"status": "maintenance"})

    return {
        "type": "parking_status",
        "total": total,
        "available": available,
        "occupied": occupied,
        "reserved": reserved,
        "maintenance": maintenance,
        "updated_at": iso_local(),
    }


async def publish_parking_status_update(db: AsyncIOMotorDatabase) -> bool:
    try:
        status = await build_parking_status(db)
        return await asyncio.to_thread(gate_mqtt_publisher.publish_parking_status, status)
    except Exception as exc:
        logger.warning("[PARKING] Failed to publish status: %s", exc)
        return False
