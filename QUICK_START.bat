@echo off
REM ============================================
REM SMART PARKING - QUICK START GUIDE
REM ============================================

color 0B
cls

echo.
echo ╔════════════════════════════════════════════════════╗
echo ║     SMART PARKING SYSTEM - QUICK START GUIDE       ║
echo ╚════════════════════════════════════════════════════╝
echo.
echo This guide will help you set up and run the system.
echo.
echo ┌────────────────────────────────────────────────────┐
echo │ STEP 1: Prerequisites                              │
echo └────────────────────────────────────────────────────┘
echo.
echo Make sure you have installed:
echo   [✓] Python 3.12+
echo   [✓] Node.js 20+
echo   [✓] PostgreSQL 15+
echo.
echo ┌────────────────────────────────────────────────────┐
echo │ STEP 2: Create Database                            │
echo └────────────────────────────────────────────────────┘
echo.
echo Open PostgreSQL and run:
echo   CREATE DATABASE smart_parking;
echo.
echo ┌────────────────────────────────────────────────────┐
echo │ STEP 3: Configure Environment                      │
echo └────────────────────────────────────────────────────┘
echo.
echo Check these files exist:
echo   - backend/.env (copy from .env.example)
echo   - frontend/.env (copy from .env.example)
echo.
echo Update backend/.env with your PostgreSQL password:
echo   POSTGRES_PASSWORD=your_password
echo.
echo ┌────────────────────────────────────────────────────┐
echo │ STEP 4: Run Setup                                  │
echo └────────────────────────────────────────────────────┘
echo.
echo Run: setup.bat
echo.
echo This will:
echo   - Install backend dependencies
echo   - Run database migrations
echo   - Seed initial data (admin/admin123)
echo   - Install frontend dependencies
echo.
echo ┌────────────────────────────────────────────────────┐
echo │ STEP 5: Start Application                          │
echo └────────────────────────────────────────────────────┘
echo.
echo Run: START.bat
echo.
echo This will open:
echo   - Backend:  http://localhost:8000
echo   - Frontend: http://localhost:5173
echo   - API Docs: http://localhost:8000/docs
echo.
echo Login with: admin / admin123
echo.
echo ╔════════════════════════════════════════════════════╗
echo ║              Ready to start? (Y/N)                 ║
echo ╚════════════════════════════════════════════════════╝
echo.

set /p choice="Do you want to run setup.bat now? (Y/N): "
if /i "%choice%"=="Y" (
    echo.
    echo Starting setup...
    call setup.bat
) else (
    echo.
    echo Setup skipped. Run setup.bat manually when ready.
)

echo.
pause
