"""
MongoDB Database Connection
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection manager"""
    
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None
    
    @classmethod
    async def connect_db(cls):
        """Connect to MongoDB"""
        try:
            logger.info(f"Connecting to MongoDB: {settings.MONGODB_URL}")
            cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            
            # Test connection
            await cls.client.admin.command('ping')
            logger.info(f"✅ Connected to MongoDB: {settings.MONGODB_DB_NAME}")
            
            # Create indexes
            await cls.create_indexes()
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection error: {e}")
            raise
    
    @classmethod
    async def close_db(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed")
    
    @classmethod
    async def create_indexes(cls):
        """Create database indexes for better performance"""
        try:
            # Customers indexes
            await cls.db.customers.create_index([("customer_id", ASCENDING)], unique=True)
            await cls.db.customers.create_index([("phone", ASCENDING)])
            await cls.db.customers.create_index([("email", ASCENDING)])
            
            # Vehicles indexes
            await cls.db.vehicles.create_index([("vehicle_id", ASCENDING)], unique=True)
            await cls.db.vehicles.create_index([("plate_number", ASCENDING)], unique=True)
            await cls.db.vehicles.create_index([("customer_id", ASCENDING)])
            
            # RFID Cards indexes
            await cls.db.rfid_cards.create_index([("card_uid", ASCENDING)], unique=True)
            await cls.db.rfid_cards.create_index([("customer_id", ASCENDING)])
            await cls.db.rfid_cards.create_index([("vehicle_id", ASCENDING)])
            
            # Sessions indexes
            await cls.db.sessions.create_index([("session_id", ASCENDING)], unique=True)
            await cls.db.sessions.create_index([("card_uid", ASCENDING)])
            await cls.db.sessions.create_index([("status", ASCENDING)])
            await cls.db.sessions.create_index([("entry_time", DESCENDING)])
            
            # Parking Slots indexes
            await cls.db.parking_slots.create_index([("slot_id", ASCENDING)], unique=True)
            await cls.db.parking_slots.create_index([("status", ASCENDING)])
            
            # Packages indexes
            await cls.db.packages.create_index([("package_id", ASCENDING)], unique=True)
            await cls.db.packages.create_index([("customer_id", ASCENDING)])
            await cls.db.packages.create_index([("status", ASCENDING)])
            await cls.db.packages.create_index([("expire_date", ASCENDING)])
            
            # Transactions indexes
            await cls.db.transactions.create_index([("transaction_id", ASCENDING)], unique=True)
            await cls.db.transactions.create_index([("customer_id", ASCENDING)])
            await cls.db.transactions.create_index([("created_at", DESCENDING)])
            
            logger.info("✅ Database indexes created")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get database instance"""
        return cls.db


# Dependency for FastAPI
async def get_database() -> AsyncIOMotorDatabase:
    """FastAPI dependency to get database"""
    return MongoDB.get_db()
