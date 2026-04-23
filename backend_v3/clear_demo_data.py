"""Clear demo/test data from Smart Parking database while keeping slot layout."""
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "smartparking")


async def main():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]

    await db.pending_scans.delete_many({})
    await db.transactions.delete_many({})
    await db.packages.delete_many({})
    await db.sessions.delete_many({})
    await db.rfid_cards.delete_many({})
    await db.vehicles.delete_many({})
    await db.customers.delete_many({})
    await db.counters.delete_many({})

    await db.parking_slots.update_many(
        {},
        {
            "$set": {
                "status": "available",
                "vehicle_id": None,
                "session_id": None
            }
        }
    )

    print("Cleared demo data: customers, vehicles, cards, sessions, packages, transactions, pending_scans, counters")
    print("Reset all parking slots to available")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
