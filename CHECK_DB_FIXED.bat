@echo off
REM ============================================
REM CHECK DATABASE CONNECTION
REM ============================================

echo.
echo Checking PostgreSQL connection...
echo.

cd /d "%~dp0backend"

if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first.
    pause
    exit /b 1
)

call venv\Scripts\python.exe -c "from sqlalchemy import create_engine; from app.core.config import settings; engine = create_engine(settings.database_url); conn = engine.connect(); print('✓ Database connection successful!'); conn.close()"

if errorlevel 1 (
    echo.
    echo ❌ Database connection failed!
    echo.
    echo Please check:
    echo   1. PostgreSQL is running
    echo   2. Database 'smart_parking' exists
    echo   3. Credentials in backend/.env are correct
    echo.
) else (
    echo.
    echo ✓ All checks passed!
    echo.
)

pause
