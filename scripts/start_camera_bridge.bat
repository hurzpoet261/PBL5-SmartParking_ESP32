@echo off
setlocal

cd /d "%~dp0..\backend_v3"

set PYTHON_EXE=python
if exist ".venv-py312\Scripts\python.exe" (
    set PYTHON_EXE=.venv-py312\Scripts\python.exe
)

if "%CAMERA_BRIDGE_MODE%"=="" set CAMERA_BRIDGE_MODE=full
if "%ACCESS_GATE_DIRECTION%"=="" set ACCESS_GATE_DIRECTION=auto
if "%VEHICLE_CENTER_DELAY_SEC%"=="" set VEHICLE_CENTER_DELAY_SEC=0.2
if "%BURST_COUNT%"=="" set BURST_COUNT=2
if "%BURST_INTERVAL_SEC%"=="" set BURST_INTERVAL_SEC=0.1
if "%ESP32_CAM_CONNECT_TIMEOUT%"=="" set ESP32_CAM_CONNECT_TIMEOUT=1.0
if "%ESP32_CAM_READ_TIMEOUT%"=="" set ESP32_CAM_READ_TIMEOUT=3.5
if "%STORE_CAPTURED_IMAGES_IN_DB%"=="" set STORE_CAPTURED_IMAGES_IN_DB=false
if "%BACKEND_API_BASE_URL%"=="" set BACKEND_API_BASE_URL=http://localhost:8000/api/v1
rem ESP32_CAM_URL is loaded from backend_v3\.env unless set in this terminal.
if "%PLATE_DETECTOR_MODEL%"=="" set PLATE_DETECTOR_MODEL=%CD%\models\license_plate_detector.pt
if "%PLATE_DETECTOR_CONF%"=="" set PLATE_DETECTOR_CONF=0.35
if "%PLATE_DETECTOR_FALLBACK_FULL_IMAGE%"=="" set PLATE_DETECTOR_FALLBACK_FULL_IMAGE=true
if "%PADDLEOCR_LANG%"=="" set PADDLEOCR_LANG=en
if "%OCR_TIMEOUT_SEC%"=="" set OCR_TIMEOUT_SEC=3.5
if "%OCR_MAX_IMAGES%"=="" set OCR_MAX_IMAGES=2
if "%CAMERA_BRIDGE_SLA_SEC%"=="" set CAMERA_BRIDGE_SLA_SEC=10
if "%BACKEND_SLA_RESERVE_SEC%"=="" set BACKEND_SLA_RESERVE_SEC=1.0
if "%ADAPTIVE_THIRD_FRAME%"=="" set ADAPTIVE_THIRD_FRAME=false
if "%ADAPTIVE_MAX_BURST_COUNT%"=="" set ADAPTIVE_MAX_BURST_COUNT=2
if "%UPLOAD_SELECTED_FRAMES_ONLY%"=="" set UPLOAD_SELECTED_FRAMES_ONLY=true
if "%OCR_FAST_VARIANTS%"=="" set OCR_FAST_VARIANTS=true
if "%OCR_MAX_VARIANTS_PER_CROP%"=="" set OCR_MAX_VARIANTS_PER_CROP=3
if "%REGISTRATION_MODE_CHECK_TIMEOUT%"=="" set REGISTRATION_MODE_CHECK_TIMEOUT=0.6

echo Starting Smart Parking Camera Bridge...
echo Mode: %CAMERA_BRIDGE_MODE%
echo Gate direction: %ACCESS_GATE_DIRECTION%
echo Backend: %BACKEND_API_BASE_URL%
if "%ESP32_CAM_URL%"=="" (
    echo ESP32-CAM: backend_v3\.env
) else (
    echo ESP32-CAM: %ESP32_CAM_URL%
)
echo Plate detector: %PLATE_DETECTOR_MODEL%
echo Camera: burst=%BURST_COUNT% interval=%BURST_INTERVAL_SEC%s ocr_images=%OCR_MAX_IMAGES% timeout=%OCR_TIMEOUT_SEC%s
echo Camera timeout: connect=%ESP32_CAM_CONNECT_TIMEOUT%s read=%ESP32_CAM_READ_TIMEOUT%s
echo SLA: %CAMERA_BRIDGE_SLA_SEC%s backend_reserve=%BACKEND_SLA_RESERVE_SEC%s adaptive_third=%ADAPTIVE_THIRD_FRAME% upload_selected=%UPLOAD_SELECTED_FRAMES_ONLY% fast_variants=%OCR_FAST_VARIANTS%
if "%ESP32_CAM_URL%"=="http://<IP_ESP32_CAM>/capture" (
    echo.
    echo ERROR: Set ESP32_CAM_URL to the real ESP32-CAM capture URL first.
    echo Example: set ESP32_CAM_URL=http://192.168.1.50/capture
    pause
    exit /b 1
)
%PYTHON_EXE% camera_bridge.py

pause
