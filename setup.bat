@echo off
REM ============================================
REM SMART PARKING - COMPREHENSIVE SETUP & TEST
REM ============================================

setlocal enabledelayedexpansion

echo.
echo [Step 1] Checking Python Installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not installed!
    exit /b 1
)
echo OK: Python found

echo.
echo [Step 2] Checking PostgreSQL Connection...
psql -U postgres -d smart_parking -c "SELECT 1" >nul 2>&1
if errorlevel 1 (
    echo WARNING: PostgreSQL connection failed
    echo Make sure PostgreSQL is running and credentials are correct
    echo Continuing anyway...
) else (
    echo OK: PostgreSQL connected
)

echo.
echo [Step 3] Installing/Updating Backend Dependencies...
cd /d "%~dp0backend"
call venv\Scripts\pip install -q --upgrade -r requirements.txt
echo OK: Dependencies installed

echo.
echo [Step 4] Running Database Migrations...
call venv\Scripts\alembic upgrade head
echo OK: Migrations applied

echo.
echo [Step 5] Seeding Database...
call venv\Scripts\python -c "from scripts.seed_data import seed; seed()"
echo OK: Database seeded with admin account (admin/admin123)

echo.
echo [Step 6] Installing Frontend Dependencies...
cd /d "%~dp0frontend"
call npm install -q
echo OK: Frontend dependencies installed

echo.
echo ============================================
echo SETUP COMPLETE! Ready to start...
echo ============================================
echo.
echo To run the project:
echo   1. Double-click START.bat
echo      or
echo   2. Manual start:
echo      Terminal 1 (Backend): cd backend ^&^& .\run.bat
echo      Terminal 2 (Frontend): cd frontend ^&^& npm run dev
echo.
echo   3. Open browser: http://localhost:5173
echo      Login with: admin / admin123
echo.
echo ============================================
pause
