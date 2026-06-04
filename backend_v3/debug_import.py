"""
Debug script to test camera_bridge imports
"""
import sys
import os

# Add backend_v3 to path
backend_dir = os.path.dirname(__file__)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

print("=" * 80)
print("DEBUGGING CAMERA BRIDGE IMPORT")
print("=" * 80)

print(f"\n1. Current working directory: {os.getcwd()}")
print(f"2. Backend directory: {backend_dir}")
print(f"3. sys.path[0]: {sys.path[0]}")

# Try importing step by step
print("\n" + "=" * 80)
print("STEP-BY-STEP IMPORT TEST")
print("=" * 80)

# Step 1: Check if camera_bridge.py exists
print("\n[1] Checking if camera_bridge.py exists...")
cb_path = os.path.join(backend_dir, "camera_bridge.py")
if os.path.exists(cb_path):
    print(f"✅ Found: {cb_path}")
else:
    print(f"❌ NOT FOUND: {cb_path}")
    sys.exit(1)

# Step 2: Try importing external dependencies
print("\n[2] Testing external dependencies...")
deps = ['requests', 'opencv_cv2', 'easyocr', 'pymongo', 'paho', 'logging', 're', 'time', 'os', 'sys']
for dep in deps:
    try:
        if dep == 'opencv_cv2':
            import cv2
            print(f"  ✅ cv2 (opencv-python)")
        elif dep == 'paho':
            import paho.mqtt.client
            print(f"  ✅ paho.mqtt.client")
        else:
            __import__(dep)
            print(f"  ✅ {dep}")
    except ImportError as e:
        print(f"  ❌ {dep}: {e}")

# Step 3: Try importing app modules
print("\n[3] Testing app modules...")
try:
    from app.config.settings import settings
    print(f"  ✅ app.config.settings")
except Exception as e:
    print(f"  ❌ app.config.settings: {e}")

# Step 4: Try importing camera_bridge
print("\n[4] Attempting to import camera_bridge...")
try:
    import camera_bridge as cb
    print(f"✅ Successfully imported camera_bridge")
    print(f"\n   Checking attributes:")
    print(f"   - ocr_reader: {hasattr(cb, 'ocr_reader')}")
    print(f"   - db: {hasattr(cb, 'db')}")
    print(f"   - task_queue: {hasattr(cb, 'task_queue')}")
    print(f"   - preprocess_image: {hasattr(cb, 'preprocess_image')}")
    print(f"   - extract_plate_number: {hasattr(cb, 'extract_plate_number')}")
    print(f"   - verify_vehicle_ownership: {hasattr(cb, 'verify_vehicle_ownership')}")
except Exception as e:
    print(f"❌ Failed to import camera_bridge:")
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("DEBUG COMPLETE")
print("=" * 80)
