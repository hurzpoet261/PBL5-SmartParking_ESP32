"""
Smart Parking API V3.0 - Main Application
MongoDB + Enhanced Features
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database.mongodb import MongoDB
from app.controllers import (
    rfid_controller,
    customer_controller,
    vehicle_controller,
    session_controller,
    slot_controller,
    package_controller,
    stats_controller
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting Smart Parking API V3.0...")
    await MongoDB.connect_db()
    logger.info("✅ Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    await MongoDB.close_db()
    logger.info("✅ Application stopped")


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"📥 {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"📤 {response.status_code}")
    return response


# ═══════════════════════════════════════════════════
# ROOT ENDPOINTS
# ═══════════════════════════════════════════════════

@app.get("/")
async def root():
    """API information"""
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "status": "online",
        "database": "MongoDB",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "rfid_scan": "POST /api/v1/rfid/scan",
            "customers": "/api/v1/customers",
            "vehicles": "/api/v1/vehicles",
            "sessions": "/api/v1/sessions",
            "slots": "/api/v1/slots",
            "packages": "/api/v1/packages",
            "stats": "/api/v1/stats"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        db = MongoDB.get_db()
        # Test database connection
        await db.command('ping')
        
        # Get counts
        customers_count = await db.customers.count_documents({})
        vehicles_count = await db.vehicles.count_documents({})
        sessions_count = await db.sessions.count_documents({})
        active_sessions = await db.sessions.count_documents({"status": "in_progress"})
        
        return {
            "status": "healthy",
            "database": "connected",
            "collections": {
                "customers": customers_count,
                "vehicles": vehicles_count,
                "sessions": sessions_count,
                "active_sessions": active_sessions
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


# ═══════════════════════════════════════════════════
# INCLUDE ROUTERS
# ═══════════════════════════════════════════════════

# RFID Controller
app.include_router(
    rfid_controller.router,
    prefix="/api/v1/rfid",
    tags=["RFID"]
)

# Customer Controller
app.include_router(
    customer_controller.router,
    prefix="/api/v1/customers",
    tags=["Customers"]
)

# Vehicle Controller
app.include_router(
    vehicle_controller.router,
    prefix="/api/v1/vehicles",
    tags=["Vehicles"]
)

# Session Controller
app.include_router(
    session_controller.router,
    prefix="/api/v1/sessions",
    tags=["Sessions"]
)

# Parking Slot Controller
app.include_router(
    slot_controller.router,
    prefix="/api/v1/slots",
    tags=["Parking Slots"]
)

# Package Controller
app.include_router(
    package_controller.router,
    prefix="/api/v1/packages",
    tags=["Packages"]
)

# Stats Controller
app.include_router(
    stats_controller.router,
    prefix="/api/v1/stats",
    tags=["Statistics"]
)


# ═══════════════════════════════════════════════════
# ERROR HANDLERS
# ═══════════════════════════════════════════════════

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


# ═══════════════════════════════════════════════════
# RUN SERVER
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print(f"  🚗 {settings.API_TITLE}")
    print("=" * 70)
    print(f"  Server:   http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"  API Docs: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    print(f"  Health:   http://{settings.API_HOST}:{settings.API_PORT}/health")
    print(f"  Database: MongoDB ({settings.MONGODB_DB_NAME})")
    print("=" * 70)
    print()
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        log_level="info"
    )
