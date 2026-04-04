@echo off
REM ============================================
REM SMART PARKING - START PROJECT
REM ============================================

color 0A
cls

echo.
echo ╔════════════════════════════════════════════════════╗
echo ║        SMART PARKING SYSTEM - STARTUP              ║
echo ║                                                    ║
echo ║  Backend:  http://localhost:8000                  ║
echo ║  Frontend: http://localhost:5173                  ║
echo ║  API Docs: http://localhost:8000/docs             ║
echo ║                                                    ║
echo ║  Login: admin / admin123                          ║
echo ╚════════════════════════════════════════════════════╝
echo.

Set "BACKEND_PATH=%~dp0backend"
Set "FRONTEND_PATH=%~dp0frontend"

REM Check if paths exist
if not exist "%BACKEND_PATH%" (
    color 0C
    echo ERROR: Backend path not found: %BACKEND_PATH%
    pause
    exit /b 1
)

if not exist "%FRONTEND_PATH%" (
    color 0C
    echo ERROR: Frontend path not found: %FRONTEND_PATH%
    pause
    exit /b 1
)

echo [1/2] Starting Backend (Port 8000)...
echo       Window will open in a few seconds...
echo.

REM Start Backend in new window
start "SmartParking Backend" cmd /k "cd /d %BACKEND_PATH% && call run.bat"

REM Wait a bit for backend to start
timeout /t 3 /nobreak

echo [2/2] Starting Frontend (Port 5173)...
echo       Window will open in a few seconds...
echo.

REM Start Frontend in new window
start "SmartParking Frontend" cmd /k "cd /d %FRONTEND_PATH% && call npm run dev"

REM Wait a bit
timeout /t 3 /nobreak

echo.
echo ╔════════════════════════════════════════════════════╗
echo ║                ✓ BOTH SERVICES STARTED             ║
echo ║                                                    ║
echo ║  Preparing services... Please wait...             ║
echo ║                                                    ║
echo ║  If browsers don't open automatically:            ║
echo ║                                                    ║
echo ║  • Backend:  http://localhost:8000/docs           ║
echo ║  • Frontend: http://localhost:5173/login          ║
echo ║                                                    ║
echo ║  Note: Services may take 10-15 seconds to start   ║
echo ╚════════════════════════════════════════════════════╝
echo.

timeout /t 5 /nobreak

@echo off
start http://localhost:5173/login
start http://localhost:8000/docs

echo.
echo ✓ Setup complete! Browser windows should open.
echo.
echo Press any key to close this window...
pause > nul
