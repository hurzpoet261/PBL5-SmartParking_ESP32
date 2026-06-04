"""
Camera Bridge Test Script
Script để test các FastAPI endpoints của camera_bridge
"""

import requests
import json
import sys
from pathlib import Path
from typing import Optional

# Configuration
API_BASE_URL = "http://localhost:8000"
CAMERA_BRIDGE_BASE = f"{API_BASE_URL}/api/v1/camera_bridge"

# Colors for console output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

def print_response(response: requests.Response):
    """Pretty print API response"""
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(response.text)

# ==============================================================================
# TEST FUNCTIONS
# ==============================================================================

def test_status():
    """Test camera bridge status"""
    print_header("1. TEST CAMERA BRIDGE STATUS")
    try:
        url = f"{CAMERA_BRIDGE_BASE}/status"
        print_info(f"GET {url}")
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print_success("Status check successful")
            print_response(response)
        else:
            print_error(f"Status check failed: {response.status_code}")
            print_response(response)
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to API at {API_BASE_URL}")
        print_warning("Make sure FastAPI server is running: python -m uvicorn app.main:app --reload")
    except Exception as e:
        print_error(f"Error: {e}")

def test_trigger_manual(card_uid: str = "0xa3d6ce05"):
    """Test manual RFID trigger"""
    print_header("2. TEST MANUAL RFID TRIGGER")
    try:
        url = f"{CAMERA_BRIDGE_BASE}/trigger-manual"
        payload = {
            "card_uid": card_uid,
            "description": "Test trigger from API"
        }
        
        print_info(f"POST {url}")
        print_info(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code == 200:
            print_success("Manual trigger queued successfully")
            print_response(response)
        else:
            print_error(f"Manual trigger failed: {response.status_code}")
            print_response(response)
    except Exception as e:
        print_error(f"Error: {e}")

def test_database():
    """Test database connection"""
    print_header("3. TEST DATABASE CONNECTION")
    try:
        url = f"{CAMERA_BRIDGE_BASE}/test-database"
        print_info(f"GET {url}")
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print_success("Database test successful")
            print_response(response)
        else:
            print_error(f"Database test failed: {response.status_code}")
            print_response(response)
    except Exception as e:
        print_error(f"Error: {e}")

def test_verify_vehicle(card_uid: str = "0xa3d6ce05", plate_number: str = "43A-123.45"):
    """Test vehicle verification"""
    print_header("4. TEST VEHICLE VERIFICATION")
    try:
        url = f"{CAMERA_BRIDGE_BASE}/test-verify"
        payload = {
            "card_uid": card_uid,
            "plate_number": plate_number
        }
        
        print_info(f"POST {url}")
        print_info(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code == 200:
            print_success("Vehicle verification test completed")
            print_response(response)
        else:
            print_error(f"Vehicle verification test failed: {response.status_code}")
            print_response(response)
    except Exception as e:
        print_error(f"Error: {e}")

def test_preprocess_image(image_path: str):
    """Test image preprocessing"""
    print_header("5. TEST IMAGE PREPROCESSING")
    
    if not Path(image_path).exists():
        print_error(f"Image file not found: {image_path}")
        return
    
    try:
        url = f"{CAMERA_BRIDGE_BASE}/test-preprocess"
        print_info(f"POST {url}")
        print_info(f"Uploading file: {image_path}")
        
        with open(image_path, "rb") as f:
            files = {"image_file": (Path(image_path).name, f, "image/jpeg")}
            response = requests.post(url, files=files, timeout=10)
        
        if response.status_code == 200:
            print_success("Image preprocessing test completed")
            print_response(response)
        else:
            print_error(f"Image preprocessing test failed: {response.status_code}")
            print_response(response)
    except Exception as e:
        print_error(f"Error: {e}")

def test_ocr(image_path: str):
    """Test OCR on image"""
    print_header("6. TEST OCR")
    
    if not Path(image_path).exists():
        print_error(f"Image file not found: {image_path}")
        return
    
    try:
        url = f"{CAMERA_BRIDGE_BASE}/test-ocr"
        print_info(f"POST {url}")
        print_info(f"Uploading file: {image_path}")
        
        with open(image_path, "rb") as f:
            files = {"image_file": (Path(image_path).name, f, "image/jpeg")}
            response = requests.post(url, files=files, timeout=30)
        
        if response.status_code == 200:
            print_success("OCR test completed")
            print_response(response)
        else:
            print_error(f"OCR test failed: {response.status_code}")
            print_response(response)
    except Exception as e:
        print_error(f"Error: {e}")

def test_captured_images(limit: int = 10):
    """List captured images"""
    print_header("7. LIST CAPTURED IMAGES")
    try:
        url = f"{CAMERA_BRIDGE_BASE}/captured-images?limit={limit}"
        print_info(f"GET {url}")
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print_success("Captured images retrieved")
            print_response(response)
        else:
            print_error(f"Failed to retrieve images: {response.status_code}")
            print_response(response)
    except Exception as e:
        print_error(f"Error: {e}")

def show_workflow_example():
    """Show example workflow"""
    print_header("EXAMPLE WORKFLOW")
    try:
        url = f"{CAMERA_BRIDGE_BASE}/test/example-workflow"
        print_info(f"GET {url}")
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print_success("Workflow example retrieved")
            print_response(response)
        else:
            print_error(f"Failed to retrieve workflow: {response.status_code}")
            print_response(response)
    except Exception as e:
        print_error(f"Error: {e}")

# ==============================================================================
# INTERACTIVE MENU
# ==============================================================================

def show_menu():
    """Display interactive menu"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}Camera Bridge Test Script{Colors.RESET}")
    print(f"{Colors.CYAN}API Base URL: {API_BASE_URL}{Colors.RESET}")
    print(f"\n{Colors.BOLD}Available Tests:{Colors.RESET}")
    print("  1. Check camera bridge status")
    print("  2. Trigger manual RFID event")
    print("  3. Test database connection")
    print("  4. Test vehicle verification")
    print("  5. Test image preprocessing (upload file)")
    print("  6. Test OCR (upload file)")
    print("  7. List captured images")
    print("  8. Show example workflow")
    print("  9. Run all tests (basic)")
    print("  0. Exit")

def run_all_basic_tests():
    """Run all basic tests"""
    print_header("RUNNING ALL BASIC TESTS")
    
    test_status()
    test_database()
    test_trigger_manual()
    test_verify_vehicle()
    test_captured_images()
    
    print_header("ALL BASIC TESTS COMPLETED")

def interactive_menu():
    """Run interactive menu"""
    while True:
        show_menu()
        choice = input(f"\n{Colors.BOLD}Select test (0-9): {Colors.RESET}").strip()
        
        if choice == "0":
            print_success("Goodbye!")
            break
        elif choice == "1":
            test_status()
        elif choice == "2":
            card_uid = input("Enter card UID (default: 0xa3d6ce05): ").strip() or "0xa3d6ce05"
            test_trigger_manual(card_uid)
        elif choice == "3":
            test_database()
        elif choice == "4":
            card_uid = input("Enter card UID (default: 0xa3d6ce05): ").strip() or "0xa3d6ce05"
            plate = input("Enter plate number (default: 43A-123.45): ").strip() or "43A-123.45"
            test_verify_vehicle(card_uid, plate)
        elif choice == "5":
            image_path = input("Enter image file path: ").strip()
            if image_path:
                test_preprocess_image(image_path)
        elif choice == "6":
            image_path = input("Enter image file path: ").strip()
            if image_path:
                test_ocr(image_path)
        elif choice == "7":
            test_captured_images()
        elif choice == "8":
            show_workflow_example()
        elif choice == "9":
            run_all_basic_tests()
        else:
            print_error("Invalid choice. Please try again.")
        
        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")

# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    print_header("CAMERA BRIDGE TEST SCRIPT")
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "status":
            test_status()
        elif command == "trigger":
            card_uid = sys.argv[2] if len(sys.argv) > 2 else "0xa3d6ce05"
            test_trigger_manual(card_uid)
        elif command == "database":
            test_database()
        elif command == "verify":
            card_uid = sys.argv[2] if len(sys.argv) > 2 else "0xa3d6ce05"
            plate = sys.argv[3] if len(sys.argv) > 3 else "43A-123.45"
            test_verify_vehicle(card_uid, plate)
        elif command == "preprocess":
            image_path = sys.argv[2] if len(sys.argv) > 2 else None
            if image_path:
                test_preprocess_image(image_path)
            else:
                print_error("Please provide image path")
        elif command == "ocr":
            image_path = sys.argv[2] if len(sys.argv) > 2 else None
            if image_path:
                test_ocr(image_path)
            else:
                print_error("Please provide image path")
        elif command == "images":
            test_captured_images()
        elif command == "workflow":
            show_workflow_example()
        elif command == "all":
            run_all_basic_tests()
        else:
            print_error(f"Unknown command: {command}")
            print_info("Available commands: status, trigger, database, verify, preprocess, ocr, images, workflow, all")
    else:
        # Interactive mode
        interactive_menu()
