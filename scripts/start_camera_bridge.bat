@echo off
setlocal

cd /d "%~dp0..\backend_v3"

set PYTHON_EXE=python
if exist ".venv-py312\Scripts\python.exe" (
    set PYTHON_EXE=.venv-py312\Scripts\python.exe
)

if "%CAMERA_BRIDGE_MODE%"=="" set CAMERA_BRIDGE_MODE=full
if "%ACCESS_GATE_DIRECTION%"=="" set ACCESS_GATE_DIRECTION=auto
if "%STORE_CAPTURED_IMAGES_IN_DB%"=="" set STORE_CAPTURED_IMAGES_IN_DB=false
if "%BACKEND_API_BASE_URL%"=="" set BACKEND_API_BASE_URL=http://localhost:8000/api/v1
if "%PLATE_DETECTOR_MODEL%"=="" set PLATE_DETECTOR_MODEL=%CD%\models\license_plate_detector.pt
if "%PLATE_DETECTOR_CONF%"=="" set PLATE_DETECTOR_CONF=0.35
if "%PLATE_DETECTOR_FALLBACK_FULL_IMAGE%"=="" set PLATE_DETECTOR_FALLBACK_FULL_IMAGE=true
if "%PADDLEOCR_LANG%"=="" set PADDLEOCR_LANG=en

echo Starting Smart Parking Camera Bridge...
echo Mode: %CAMERA_BRIDGE_MODE%
echo Gate direction: %ACCESS_GATE_DIRECTION%
echo Backend: %BACKEND_API_BASE_URL%
echo Plate detector: %PLATE_DETECTOR_MODEL%
%PYTHON_EXE% camera_bridge.py

pause
