@echo off
setlocal

cd /d "%~dp0..\backend_v3"

set PYTHON_EXE=python
if exist ".venv-py312\Scripts\python.exe" (
    set PYTHON_EXE=.venv-py312\Scripts\python.exe
)

if "%CAMERA_BRIDGE_MODE%"=="" set CAMERA_BRIDGE_MODE=full
if "%ACCESS_GATE_DIRECTION%"=="" set ACCESS_GATE_DIRECTION=auto
if "%VEHICLE_CENTER_DELAY_SEC%"=="" set VEHICLE_CENTER_DELAY_SEC=0.5
if "%BURST_COUNT%"=="" set BURST_COUNT=3
if "%BURST_INTERVAL_SEC%"=="" set BURST_INTERVAL_SEC=0.15
if "%STORE_CAPTURED_IMAGES_IN_DB%"=="" set STORE_CAPTURED_IMAGES_IN_DB=false
if "%BACKEND_API_BASE_URL%"=="" set BACKEND_API_BASE_URL=http://localhost:8000/api/v1
if "%ESP32_CAM_URL%"=="" set ESP32_CAM_URL=http://<IP_ESP32_CAM>/capture
if "%PLATE_DETECTOR_MODEL%"=="" set PLATE_DETECTOR_MODEL=%CD%\models\license_plate_detector.pt
if "%PLATE_DETECTOR_CONF%"=="" set PLATE_DETECTOR_CONF=0.35
if "%PLATE_DETECTOR_FALLBACK_FULL_IMAGE%"=="" set PLATE_DETECTOR_FALLBACK_FULL_IMAGE=true
if "%PADDLEOCR_LANG%"=="" set PADDLEOCR_LANG=en
if "%OCR_TIMEOUT_SEC%"=="" set OCR_TIMEOUT_SEC=5
if "%OCR_MAX_IMAGES%"=="" set OCR_MAX_IMAGES=3

echo Starting Smart Parking Camera Bridge...
echo Mode: %CAMERA_BRIDGE_MODE%
echo Gate direction: %ACCESS_GATE_DIRECTION%
echo Backend: %BACKEND_API_BASE_URL%
echo ESP32-CAM: %ESP32_CAM_URL%
echo Plate detector: %PLATE_DETECTOR_MODEL%
echo Camera: burst=%BURST_COUNT% interval=%BURST_INTERVAL_SEC%s ocr_images=%OCR_MAX_IMAGES% timeout=%OCR_TIMEOUT_SEC%s
if "%ESP32_CAM_URL%"=="http://<IP_ESP32_CAM>/capture" (
    echo.
    echo ERROR: Set ESP32_CAM_URL to the real ESP32-CAM capture URL first.
    echo Example: set ESP32_CAM_URL=http://192.168.1.50/capture
    pause
    exit /b 1
)
%PYTHON_EXE% camera_bridge.py

pause
