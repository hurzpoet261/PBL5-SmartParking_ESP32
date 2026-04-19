"""
Initialize sample data for Smart Parking System
Run this script to create initial parking slots
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "smartparking")


async def init_parking_slots():
    """Initialize parking slots"""
    print("=" * 70)
    print("  🚗 SMART PARKING - INITIALIZE DATA")
    print("=" * 70)
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGODB_DB_NAME]
    
    try:
        # Check if slots already exist
        existing_count = await db.parking_slots.count_documents({})
        
        if existing_count > 0:
            print(f"\n⚠️  Database already has {existing_count} parking slots.")
            response = input("Do you want to reset and recreate? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Cancelled.")
                return
            
            # Delete existing slots
            await db.parking_slots.delete_many({})
            print("🗑️  Deleted existing slots.")
        
        # Create 20 parking slots
        slots = []
       # Create 20 parking slots (4 rows, 5 columns)
        slots = []
        for i in range(1, 21):
            # Tính toán tọa độ hàng và cột (ví dụ: chia thành 4 hàng, mỗi hàng 5 ô)
            row_index = (i - 1) // 5
            col_index = (i - 1) % 5
            
            slot = {
                "slot_id": f"SLOT-{i:03d}",
                "slot_number": f"A{i:02d}",
                "row": row_index,      # BỔ SUNG TRƯỜNG NÀY
                "col": col_index,      # BỔ SUNG TRƯỜNG NÀY (Thường đi kèm với row)
                "status": "available",
                "vehicle_id": None,
                "session_id": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            slots.append(slot)
        
        # Insert slots
        result = await db.parking_slots.insert_many(slots)
        print(f"\n✅ Created {len(result.inserted_ids)} parking slots!")
        
        # Show summary
        print("\n" + "=" * 70)
        print("📊 SUMMARY")
        print("=" * 70)
        print(f"Total Slots: {len(slots)}")
        print(f"Available: {len(slots)}")
        print(f"Occupied: 0")
        print("\nSlot IDs: SLOT-001 to SLOT-020")
        print("Slot Numbers: A01 to A20")
        print("=" * 70)
        print("\n✅ Initialization complete!")
        print("You can now start the backend: python -m app.main")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(init_parking_slots())
