@echo off
setlocal

set ROOT_DIR=%~dp0..
set BACKEND_DIR=%ROOT_DIR%\backend_v3
set FRONTEND_INDEX=%ROOT_DIR%\frontend_v3\index.html

set PYTHON_EXE=python
if exist "%BACKEND_DIR%\.venv-py312\Scripts\python.exe" (
    set PYTHON_EXE=%BACKEND_DIR%\.venv-py312\Scripts\python.exe
)

if "%CAMERA_BRIDGE_MODE%"=="" set CAMERA_BRIDGE_MODE=full
if "%ACCESS_GATE_DIRECTION%"=="" set ACCESS_GATE_DIRECTION=auto
if "%STORE_CAPTURED_IMAGES_IN_DB%"=="" set STORE_CAPTURED_IMAGES_IN_DB=false
if "%BACKEND_API_BASE_URL%"=="" set BACKEND_API_BASE_URL=http://localhost:8000/api/v1
if "%PLATE_DETECTOR_MODEL%"=="" set PLATE_DETECTOR_MODEL=%BACKEND_DIR%\models\license_plate_detector.pt
if "%PLATE_DETECTOR_CONF%"=="" set PLATE_DETECTOR_CONF=0.35
if "%PLATE_DETECTOR_FALLBACK_FULL_IMAGE%"=="" set PLATE_DETECTOR_FALLBACK_FULL_IMAGE=true
if "%PADDLEOCR_LANG%"=="" set PADDLEOCR_LANG=en

start "Smart Parking API V3" cmd /k "cd /d ""%BACKEND_DIR%"" && ""%PYTHON_EXE%"" -m app.main"
timeout /t 5 /nobreak >nul
start "Smart Parking Camera Bridge" cmd /k "cd /d ""%BACKEND_DIR%"" && set CAMERA_BRIDGE_MODE=%CAMERA_BRIDGE_MODE%&& set ACCESS_GATE_DIRECTION=%ACCESS_GATE_DIRECTION%&& set STORE_CAPTURED_IMAGES_IN_DB=%STORE_CAPTURED_IMAGES_IN_DB%&& set BACKEND_API_BASE_URL=%BACKEND_API_BASE_URL%&& set PLATE_DETECTOR_MODEL=%PLATE_DETECTOR_MODEL%&& set PLATE_DETECTOR_CONF=%PLATE_DETECTOR_CONF%&& set PLATE_DETECTOR_FALLBACK_FULL_IMAGE=%PLATE_DETECTOR_FALLBACK_FULL_IMAGE%&& set PADDLEOCR_LANG=%PADDLEOCR_LANG%&& ""%PYTHON_EXE%"" camera_bridge.py"

if exist "%FRONTEND_INDEX%" (
    start "" "%FRONTEND_INDEX%"
)

echo.
echo Smart Parking system started.
echo Backend:  http://localhost:8000
echo Frontend: %FRONTEND_INDEX%
echo Bridge:   %BACKEND_API_BASE_URL%/access-events/rfid-camera
echo Gate:     %ACCESS_GATE_DIRECTION%
echo Detector: %PLATE_DETECTOR_MODEL%
echo.
pause
