@echo off
setlocal

set ROOT_DIR=%~dp0..
set BACKEND_DIR=%ROOT_DIR%\backend_v3

if not "%BACKEND_PYTHON_EXE%"=="" (
    set PYTHON_EXE=%BACKEND_PYTHON_EXE%
) else if not "%TRAIN_PYTHON_EXE%"=="" (
    set PYTHON_EXE=%TRAIN_PYTHON_EXE%
) else (
    set PYTHON_EXE=C:\Users\Admin\miniconda3\envs\pbl5-ai\python.exe
)

echo Installing backend runtime dependencies...
"%PYTHON_EXE%" -m pip install -r "%BACKEND_DIR%\requirements.txt"
if errorlevel 1 (
    echo Backend dependency installation failed.
    pause
    exit /b 1
)

echo.
echo Installing PaddleOCR without PDF/docx dependencies...
"%PYTHON_EXE%" -m pip install paddleocr==2.7.0.3 --no-deps
if errorlevel 1 (
    echo PaddleOCR installation failed.
    pause
    exit /b 1
)

echo.
echo Verifying backend AI runtime...
"%PYTHON_EXE%" -c "import cv2, numpy, torch, paddle; from ultralytics import YOLO; from paddleocr import PaddleOCR; print('cv2', cv2.__version__); print('numpy', numpy.__version__); print('torch', torch.__version__, 'cuda', torch.cuda.is_available()); print('paddle', paddle.__version__); print('paddleocr import ok')"
if errorlevel 1 (
    echo Runtime verification failed.
    pause
    exit /b 1
)

echo.
echo Backend runtime is ready.
pause
