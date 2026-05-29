"""
Camera Bridge Test Controller
Endpoints to test camera_bridge functionality without MQTT
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import sys
import logging
import tempfile
import time
from pathlib import Path

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter()

# ==============================================================================
# Import camera_bridge functions (dynamic import để tránh circular dependency)
# ==============================================================================
def get_camera_bridge_module():
    """Dynamically import camera_bridge module"""
    try:
        # Calculate path: app/controllers -> app -> backend_v3
        controller_dir = os.path.dirname(__file__)
        app_dir = os.path.dirname(controller_dir)
        backend_dir = os.path.dirname(app_dir)

        logger.debug(f"Controller dir: {controller_dir}")
        logger.debug(f"Backend dir: {backend_dir}")

        # Add backend_v3 to sys.path if not already there
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
            logger.debug(f"Added {backend_dir} to sys.path")

        # Import camera_bridge from backend_v3 root
        import camera_bridge as cb_module
        logger.info("✅ Successfully imported camera_bridge module")
        return cb_module

    except ImportError as e:
        logger.error(f"❌ ImportError: Failed to import camera_bridge: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error importing camera_bridge: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# Lazy load camera_bridge - not loaded at module init
camera_bridge = None

def get_camera_bridge():
    """Get or load camera_bridge module"""
    global camera_bridge
    if camera_bridge is None:
        camera_bridge = get_camera_bridge_module()
    return camera_bridge

# ==============================================================================
# PYDANTIC MODELS
# ==============================================================================

class ManualTriggerRequest(BaseModel):
    """Request to trigger camera_bridge manually"""
    card_uid: str
    description: Optional[str] = None


class OCRTestRequest(BaseModel):
    """Request to test OCR on a specific image"""
    image_path: str
    timeout: float = 2.0


class VerifyVehicleRequest(BaseModel):
    """Request to verify vehicle ownership"""
    card_uid: str
    plate_number: str


class TestResponse(BaseModel):
    """Generic test response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get("/status")
async def get_bridge_status():
    """Get camera bridge status"""
    try:
        cb = get_camera_bridge()
        if not cb:
            raise HTTPException(status_code=503, detail="Camera bridge not available - failed to load module")

        queue_size = cb.task_queue.qsize()
        runtime = getattr(cb, "runtime", None)

        return {
            "status": "online",
            "ocr_model_loaded": bool(getattr(runtime, "ocr_loaded", False)),
            "plate_detector_loaded": bool(getattr(runtime, "detector_loaded", False)),
            "mongodb_connected": cb.db is not None,
            "mqtt_client": "configured",
            "queue_size": queue_size,
            "config": {
                "burst_count": cb.BURST_COUNT,
                "esp32_cam_url": cb.ESP32_CAM_URL,
                "mqtt_broker": cb.MQTT_BROKER,
                "save_dir": cb.SAVE_DIR,
                "store_captured_images_in_db": cb.STORE_CAPTURED_IMAGES_IN_DB,
                "capture_metadata_collection": cb.CAPTURE_METADATA_COLLECTION,
                "plate_detector_model": cb.PLATE_DETECTOR_MODEL,
                "backend_access_event_url": cb.BACKEND_ACCESS_EVENT_URL
            }
        }
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-manual")
async def trigger_manual_rfid(request: ManualTriggerRequest):
    """Manually trigger camera_bridge without MQTT"""
    try:
        cb = get_camera_bridge()
        if not cb:
            raise HTTPException(status_code=503, detail="Camera bridge not available - failed to load module")

        card_uid = request.card_uid.strip()
        if not card_uid:
            raise HTTPException(status_code=400, detail="card_uid cannot be empty")

        logger.info(f"🔔 Manual trigger: UID={card_uid}")
        event = cb.RFIDEvent(card_uid=card_uid, received_at=time.time())
        cb.task_queue.put_nowait(event)

        return {
            "success": True,
            "message": f"RFID event queued for processing",
            "card_uid": card_uid,
            "queue_size": cb.task_queue.qsize()
        }
    except Exception as e:
        logger.error(f"Manual trigger error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-ocr")
async def test_ocr(image_file: UploadFile = File(...)):
    """Test OCR on uploaded image"""
    try:
        cb = get_camera_bridge()
        if not cb:
            raise HTTPException(status_code=503, detail="Camera bridge not available - failed to load module")

        cb.init_resources()
        if not getattr(cb.runtime, "ocr_loaded", False):
            raise HTTPException(status_code=503, detail="PaddleOCR model not loaded")

        # Save uploaded file to temp directory
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            content = await image_file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Test preprocessing
            logger.info(f"Testing OCR on: {image_file.filename}")
            preprocessed = cb.preprocess_image(tmp_path)

            if preprocessed is None:
                raise HTTPException(status_code=400, detail="Failed to preprocess image")

            # Extract plate number
            plate_number, confidence = cb.extract_plate_number([tmp_path], timeout=2.0)

            return {
                "success": True,
                "message": "OCR test completed",
                "filename": image_file.filename,
                "results": {
                    "plate_number": plate_number,
                    "confidence": float(confidence) if confidence else 0,
                    "detected": plate_number is not None
                }
            }
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-preprocess")
async def test_preprocess(image_file: UploadFile = File(...)):
    """Test image preprocessing only"""
    try:
        cb = get_camera_bridge()
        if not cb:
            raise HTTPException(status_code=503, detail="Camera bridge not available - failed to load module")

        # Save uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            content = await image_file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            logger.info(f"Testing preprocessing on: {image_file.filename}")
            preprocessed = cb.preprocess_image(tmp_path)

            if preprocessed is None:
                raise HTTPException(status_code=400, detail="Failed to preprocess image")

            # Save preprocessed image for reference
            output_path = os.path.join(cb.SAVE_DIR, f"preprocessed_{image_file.filename}")
            import cv2
            cv2.imwrite(output_path, preprocessed)

            return {
                "success": True,
                "message": "Preprocessing test completed",
                "filename": image_file.filename,
                "output_saved": output_path,
                "image_shape": preprocessed.shape,
                "image_dtype": str(preprocessed.dtype)
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preprocess test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-verify")
async def test_verify_vehicle(request: VerifyVehicleRequest):
    """Test database verification"""
    try:
        cb = get_camera_bridge()
        if not cb:
            raise HTTPException(status_code=503, detail="Camera bridge not available - failed to load module")

        if cb.db is None:
            raise HTTPException(status_code=503, detail="Database not connected")

        card_uid = request.card_uid.strip()
        plate_number = request.plate_number.strip().upper()

        if not card_uid or not plate_number:
            raise HTTPException(status_code=400, detail="card_uid and plate_number required")

        logger.info(f"Testing DB verification: UID={card_uid}, Plate={plate_number}")

        result = cb.verify_vehicle_ownership(card_uid, plate_number)

        return {
            "success": True,
            "message": "Verification test completed",
            "verification_result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verify test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-database")
async def test_database_connection():
    """Test MongoDB connection and collections"""
    try:
        cb = get_camera_bridge()
        if not cb:
            raise HTTPException(status_code=503, detail="Camera bridge not available - failed to load module")

        if cb.db is None:
            raise HTTPException(status_code=503, detail="Database not connected")

        db = cb.db

        # Test collections
        collections_info = {}
        collections = ['rfid_cards', 'vehicles', 'customers', 'sessions']

        for collection_name in collections:
            try:
                count = db[collection_name].count_documents({})
                collections_info[collection_name] = {
                    "count": count,
                    "available": True
                }
            except Exception as e:
                collections_info[collection_name] = {
                    "count": 0,
                    "available": False,
                    "error": str(e)
                }

        return {
            "success": True,
            "message": "Database test completed",
            "database": db.name,
            "collections": collections_info
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/captured-images")
async def list_captured_images(limit: int = Query(10, ge=1, le=100)):
    """List recently captured images"""
    try:
        cb = get_camera_bridge()
        if not cb:
            raise HTTPException(status_code=503, detail="Camera bridge not available - failed to load module")

        save_dir = cb.SAVE_DIR

        # Get image files sorted by modification time
        images = []
        if os.path.exists(save_dir):
            for filename in os.listdir(save_dir):
                filepath = os.path.join(save_dir, filename)
                if os.path.isfile(filepath) and filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    mtime = os.path.getmtime(filepath)
                    images.append({
                        "filename": filename,
                        "path": filepath,
                        "size": os.path.getsize(filepath),
                        "timestamp": mtime
                    })

        # Sort by timestamp (newest first) and limit
        images = sorted(images, key=lambda x: x['timestamp'], reverse=True)[:limit]

        database_images = []
        if cb.db is not None:
            cursor = (
                cb.db[cb.CAPTURE_METADATA_COLLECTION]
                .find(
                    {},
                    {
                        "_id": 0,
                        "filename": 1,
                        "card_uid": 1,
                        "capture_batch_id": 1,
                        "frame_no": 1,
                        "captured_at": 1,
                        "byte_size": 1,
                        "gridfs_file_id": 1,
                        "local_path": 1,
                    },
                )
                .sort("captured_at", -1)
                .limit(limit)
            )
            for doc in cursor:
                if doc.get("captured_at") is not None:
                    doc["captured_at"] = doc["captured_at"].isoformat()
                if doc.get("gridfs_file_id") is not None:
                    doc["gridfs_file_id"] = str(doc["gridfs_file_id"])
                database_images.append(doc)

        return {
            "success": True,
            "message": f"Found {len(images)} local images and {len(database_images)} database images",
            "save_dir": save_dir,
            "images": images,
            "database_images": database_images,
            "total": len(images),
            "database_total": len(database_images)
        }

    except Exception as e:
        logger.error(f"List images error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/example-workflow")
async def example_workflow():
    """Return example workflow for testing"""
    return {
        "title": "Camera Bridge Test Workflow",
        "steps": [
            {
                "step": 1,
                "description": "Check camera bridge status",
                "endpoint": "GET /api/v1/camera_bridge/status"
            },
            {
                "step": 2,
                "description": "Manually trigger RFID event",
                "endpoint": "POST /api/v1/camera_bridge/trigger-manual",
                "body": {
                    "card_uid": "0xa3d6ce05",
                    "description": "Test RFID card"
                }
            },
            {
                "step": 3,
                "description": "Upload and test OCR",
                "endpoint": "POST /api/v1/camera_bridge/test-ocr",
                "body": "multipart/form-data (image_file)"
            },
            {
                "step": 4,
                "description": "Test image preprocessing",
                "endpoint": "POST /api/v1/camera_bridge/test-preprocess",
                "body": "multipart/form-data (image_file)"
            },
            {
                "step": 5,
                "description": "Test vehicle verification",
                "endpoint": "POST /api/v1/camera_bridge/test-verify",
                "body": {
                    "card_uid": "0xa3d6ce05",
                    "plate_number": "43A-123.45"
                }
            },
            {
                "step": 6,
                "description": "Test database connection",
                "endpoint": "GET /api/v1/camera_bridge/test-database"
            },
            {
                "step": 7,
                "description": "List captured images",
                "endpoint": "GET /api/v1/camera_bridge/captured-images?limit=10"
            }
        ]
    }
