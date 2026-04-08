"""
ID Generator Utility
"""
from motor.motor_asyncio import AsyncIOMotorDatabase


async def generate_id(db: AsyncIOMotorDatabase, collection_name: str, prefix: str) -> str:
    """
    Generate unique ID for a collection
    
    Args:
        db: Database instance
        collection_name: Name of collection
        prefix: ID prefix (C, V, S, P, T, etc.)
    
    Returns:
        Generated ID (e.g., C000001, V000001)
    """
    collection = db[collection_name]
    
    # Get the last document
    last_doc = await collection.find_one(
        sort=[(f"{prefix.lower()}_id" if collection_name != "rfid_cards" else "card_uid", -1)]
    )
    
    if not last_doc:
        return f"{prefix}000001"
    
    # Extract number from last ID
    id_field = f"{collection_name[:-1]}_id" if collection_name.endswith('s') else f"{collection_name}_id"
    
    if collection_name == "customers":
        last_id = last_doc.get("customer_id", f"{prefix}000000")
    elif collection_name == "vehicles":
        last_id = last_doc.get("vehicle_id", f"{prefix}000000")
    elif collection_name == "sessions":
        last_id = last_doc.get("session_id", f"{prefix}000000")
    elif collection_name == "packages":
        last_id = last_doc.get("package_id", f"{prefix}000000")
    elif collection_name == "transactions":
        last_id = last_doc.get("transaction_id", f"{prefix}000000")
    else:
        last_id = f"{prefix}000000"
    
    # Extract number
    try:
        number = int(last_id[len(prefix):])
        next_number = number + 1
        return f"{prefix}{next_number:06d}"
    except:
        return f"{prefix}000001"
