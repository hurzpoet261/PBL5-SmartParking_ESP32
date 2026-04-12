"""
Check MongoDB Connection and Provide Recommendations
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "smartparking")

print("=" * 70)
print("  🔍 SMART PARKING - MONGODB CONNECTION CHECK")
print("=" * 70)
print()

# Mask password in URL for display
def mask_password(url):
    if '@' in url and ':' in url:
        try:
            parts = url.split('@')
            user_pass = parts[0].split('//')[-1]
            user = user_pass.split(':')[0]
            return url.replace(user_pass, f"{user}:****")
        except:
            return url
    return url

print(f"📋 Current Configuration:")
print(f"   URL: {mask_password(MONGODB_URL)}")
print(f"   Database: {MONGODB_DB_NAME}")
print()

async def test_connection(url, name, timeout=10000):
    """Test MongoDB connection"""
    try:
        print(f"🔌 Testing {name}...", end=" ", flush=True)
        
        client = AsyncIOMotorClient(
            url,
            serverSelectionTimeoutMS=timeout
        )
        
        # Test connection
        await client.admin.command('ping')
        
        # Get database info
        db = client[MONGODB_DB_NAME]
        collections = await db.list_collection_names()
        
        # Count documents
        stats = {}
        for coll in ['customers', 'vehicles', 'sessions', 'parking_slots']:
            if coll in collections:
                count = await db[coll].count_documents({})
                stats[coll] = count
        
        client.close()
        
        print("✅ SUCCESS")
        print(f"   Collections: {len(collections)}")
        if stats:
            print(f"   Data: {stats}")
        
        return True
        
    except Exception as e:
        print("❌ FAILED")
        error_msg = str(e)
        if "SSL" in error_msg or "TLS" in error_msg:
            print(f"   Error: SSL/TLS handshake failed")
            print(f"   Reason: Certificate or encryption issue")
        elif "Authentication" in error_msg:
            print(f"   Error: Authentication failed")
            print(f"   Reason: Wrong username or password")
        elif "timeout" in error_msg.lower():
            print(f"   Error: Connection timeout")
            print(f"   Reason: Cannot reach server (firewall/network)")
        else:
            print(f"   Error: {error_msg[:100]}")
        
        return False

async def main():
    """Main test function"""
    
    # Test 1: Current configuration
    print("=" * 70)
    print("TEST 1: Current Configuration (.env)")
    print("=" * 70)
    current_works = await test_connection(MONGODB_URL, "Current Config", 15000)
    print()
    
    # Test 2: Local MongoDB
    print("=" * 70)
    print("TEST 2: Local MongoDB")
    print("=" * 70)
    local_works = await test_connection("mongodb://localhost:27017", "Local MongoDB", 5000)
    print()
    
    # Recommendations
    print("=" * 70)
    print("📊 RESULTS & RECOMMENDATIONS")
    print("=" * 70)
    print()
    
    if current_works:
        print("✅ Your current configuration is working!")
        print("   You can start the backend now:")
        print("   → python -m app.main")
        print()
        
    elif local_works:
        print("✅ Local MongoDB is working!")
        print("   Recommendation: Switch to local MongoDB for development")
        print()
        print("   Steps:")
        print("   1. Copy .env.local to .env:")
        if sys.platform == "win32":
            print("      → copy .env.local .env")
        else:
            print("      → cp .env.local .env")
        print()
        print("   2. Start backend:")
        print("      → python -m app.main")
        print()
        
    else:
        print("❌ Both connections failed!")
        print()
        print("   For MongoDB Atlas:")
        print("   1. Check internet connection")
        print("   2. Whitelist your IP in MongoDB Atlas:")
        print("      → https://cloud.mongodb.com")
        print("      → Network Access → Add IP Address → Allow from Anywhere")
        print("   3. Verify credentials are correct")
        print()
        print("   For Local MongoDB:")
        print("   1. Install MongoDB Community Edition:")
        print("      → https://www.mongodb.com/try/download/community")
        print("   2. Start MongoDB service:")
        if sys.platform == "win32":
            print("      → net start MongoDB")
        else:
            print("      → sudo systemctl start mongod")
        print("   3. Copy .env.local to .env")
        print()
    
    print("=" * 70)
    print("📁 Available Configuration Files:")
    print("=" * 70)
    print("   .env        - Current active configuration")
    print("   .env.local  - Local MongoDB configuration")
    print("   .env.atlas  - MongoDB Atlas configuration")
    print()
    print("   To switch:")
    if sys.platform == "win32":
        print("   → copy .env.local .env   (for local)")
        print("   → copy .env.atlas .env   (for atlas)")
    else:
        print("   → cp .env.local .env   (for local)")
        print("   → cp .env.atlas .env   (for atlas)")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
