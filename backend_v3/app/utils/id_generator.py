"""
ID Generator Utility
"""
import re

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument


COUNTER_KEYS = {
    "customers": "customer_id",
    "vehicles": "vehicle_id",
    "sessions": "session_id",
    "packages": "package_id",
    "transactions": "transaction_id",
    "parking_events": "event_id",
}


async def _get_max_existing_sequence(
    db: AsyncIOMotorDatabase,
    collection_name: str,
    id_field: str,
    prefix: str,
) -> int:
    pattern = f"^{re.escape(prefix)}\\d+$"
    docs = await (
        db[collection_name]
        .find({id_field: {"$regex": pattern}}, {id_field: 1, "_id": 0})
        .sort(id_field, -1)
        .limit(1)
        .to_list(length=1)
    )
    if not docs:
        return 0

    value = str(docs[0].get(id_field, ""))
    try:
        return int(value[len(prefix):])
    except ValueError:
        return 0


async def generate_id(db: AsyncIOMotorDatabase, collection_name: str, prefix: str) -> str:
    """
    Generate unique ID using an atomic counter collection.
    Falls back cleanly for supported business collections.
    """
    if collection_name not in COUNTER_KEYS:
        raise ValueError(f"Unsupported collection for ID generation: {collection_name}")

    id_field = COUNTER_KEYS[collection_name]
    max_existing_seq = await _get_max_existing_sequence(db, collection_name, id_field, prefix)
    if max_existing_seq > 0:
        await db.counters.update_one(
            {"_id": collection_name},
            {"$max": {"seq": max_existing_seq}},
            upsert=True,
        )

    counter = await db.counters.find_one_and_update(
        {"_id": collection_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    seq = counter.get("seq", 1)
    return f"{prefix}{seq:06d}"
