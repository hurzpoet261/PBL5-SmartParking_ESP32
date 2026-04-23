"""
ID Generator Utility
"""
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument


COUNTER_KEYS = {
    "customers": "customer_id",
    "vehicles": "vehicle_id",
    "sessions": "session_id",
    "packages": "package_id",
    "transactions": "transaction_id",
}


async def generate_id(db: AsyncIOMotorDatabase, collection_name: str, prefix: str) -> str:
    """
    Generate unique ID using an atomic counter collection.
    Falls back cleanly for supported business collections.
    """
    if collection_name not in COUNTER_KEYS:
        raise ValueError(f"Unsupported collection for ID generation: {collection_name}")

    counter = await db.counters.find_one_and_update(
        {"_id": collection_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    seq = counter.get("seq", 1)
    return f"{prefix}{seq:06d}"
