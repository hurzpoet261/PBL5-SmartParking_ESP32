@echo off
REM ============================================
REM VERIFY SYSTEM SETUP
REM ============================================

setlocal enabledelayedexpansion
color 0E

echo.
echo ╔════════════════════════════════════════════════════╗
echo ║        SMART PARKING - SYSTEM VERIFICATION         ║
echo ╚════════════════════════════════════════════════════╝
echo.

set "errors=0"

REM Check Python
echo [1/8] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo     ❌ Python not found
    set /a errors+=1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo     ✓ Python %%i installed
)

REM Check Node.js
echo [2/8] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo     ❌ Node.js not found
    set /a errors+=1
) else (
    for /f %%i in ('node --version') do echo     ✓ Node.js %%i installed
)

REM Check npm
echo [3/8] Checking npm...
npm --version >nul 2>&1
if errorlevel 1 (
    echo     ❌ npm not found
    set /a errors+=1
) else (
    for /f %%i in ('npm --version') do echo     ✓ npm %%i installed
)

REM Check backend venv
echo [4/8] Checking backend virtual environment...
if exist "backend\venv\Scripts\python.exe" (
    echo     ✓ Virtual environment exists
) else (
    echo     ❌ Virtual environment not found
    echo        Run: cd backend ^&^& python -m venv venv
    set /a errors+=1
)

REM Check backend .env
echo [5/8] Checking backend .env file...
if exist "backend\.env" (
    echo     ✓ backend/.env exists
) else (
    echo     ❌ backend/.env not found
    echo        Run: copy backend\.env.example backend\.env
    set /a errors+=1
)

REM Check frontend .env
echo [6/8] Checking frontend .env file...
if exist "frontend\.env" (
    echo     ✓ frontend/.env exists
) else (
    echo     ❌ frontend/.env not found
    echo        Run: copy frontend\.env.example frontend\.env
    set /a errors+=1
)

REM Check frontend node_modules
echo [7/8] Checking frontend dependencies...
if exist "frontend\node_modules" (
    echo     ✓ Frontend dependencies installed
) else (
    echo     ⚠ Frontend dependencies not installed
    echo        Run: cd frontend ^&^& npm install
)

REM Check backend packages
echo [8/8] Checking backend dependencies...
if exist "backend\venv\Scripts\python.exe" (
    cd /d "%~dp0backend"
    call venv\Scripts\python.exe -c "import fastapi" >nul 2>&1
    if errorlevel 1 (
        echo     ⚠ Backend dependencies not installed
        echo        Run: cd backend ^&^& venv\Scripts\pip install -r requirements.txt
    ) else (
        echo     ✓ Backend dependencies installed
    )
    cd /d "%~dp0"
)

echo.
echo ════════════════════════════════════════════════════
if %errors% EQU 0 (
    echo ✓ All checks passed! System is ready.
    echo.
    echo Next steps:
    echo   1. Make sure PostgreSQL is running
    echo   2. Create database: CREATE DATABASE smart_parking;
    echo   3. Run: setup.bat (if not done yet)
    echo   4. Run: START.bat
) else (
    echo ❌ Found %errors% error(s). Please fix them first.
    echo.
    echo See TROUBLESHOOTING.md for help.
)
echo ════════════════════════════════════════════════════
echo.

pause
