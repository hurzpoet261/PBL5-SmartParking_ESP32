@echo off
REM Check PostgreSQL and Database connection

color 0F
cls

echo.
echo ╔════════════════════════════════════════════════════╗
echo ║      SMART PARKING - DATABASE CHECK               ║
echo ╚════════════════════════════════════════════════════╝
echo.

echo [1/3] Checking if PostgreSQL is installed...
where psql >nul 2>&1
if errorlevel 1 (
    color 0C
    echo ✗ PostgreSQL not found in PATH
    echo.
    echo Solution:
    echo   1. Download: https://www.postgresql.org/download/windows/
    echo   2. Install and add to PATH
    echo   3. Run this script again
    echo.
    pause
    exit /b 1
) else (
    color 0A
    echo ✓ PostgreSQL found
)

echo.
echo [2/3] Checking database connection...

REM Try to connect to PostgreSQL
psql -U postgres -d smart_parking -c "SELECT 1" >nul 2>&1
if errorlevel 1 (
    color 0E
    echo ⚠ Could not connect to database
    echo.
    echo Trying to create database...
    
    REM Try to create database
    psql -U postgres -c "CREATE DATABASE smart_parking" >nul 2>&1
    if errorlevel 1 (
        color 0C
        echo ✗ Failed to create database
        echo.
        echo Troubleshooting:
        echo   1. Is PostgreSQL running? (Start from Services)
        echo   2. Is password correct? (Edit .env if needed)
        echo   3. Does user 'postgres' exist?
        echo.
        pause
        exit /b 1
    ) else (
        color 0A
        echo ✓ Database created successfully
    )
) else (
    color 0A
    echo ✓ Database connected
)

echo.
echo [3/3] Running migrations and seeding...

cd /d E:\PBL5-SmartParking_ESP32\backend

if not exist venv (
    color 0C
    echo ✗ Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

call venv\Scripts\alembic upgrade head >nul 2>&1
if errorlevel 1 (
    color 0C
    echo ✗ Migration failed!
) else (
    color 0A
    echo ✓ Migrations applied
)

call venv\Scripts\python -c "from scripts.seed_data import seed; seed()" >nul 2>&1
if errorlevel 1 (
    color 0C
    echo ✗ Seeding failed!
) else (
    color 0A
    echo ✓ Database seeded
)

echo.
echo ╔════════════════════════════════════════════════════╗
echo ║             ✓ DATABASE READY!                     ║
echo ║                                                    ║
echo ║  Admin Account Created:                           ║
echo ║  • Username: admin                                ║
echo ║  • Password: admin123                             ║
echo ║                                                    ║
echo ║  You can now run: START.bat                        ║
echo ╚════════════════════════════════════════════════════╝
echo.

pause
