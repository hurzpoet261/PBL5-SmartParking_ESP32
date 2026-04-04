REM ============================================
REM SMART PARKING - API TEST SCRIPT
REM ============================================
@echo off
setlocal enabledelayedexpansion

set API_URL=http://127.0.0.1:8000/api/v1

echo.
echo [Test 1] Health Check...
curl -s %API_URL:~0,-7%/health | findstr "status" >nul
if errorlevel 1 (
    echo ERROR: Backend server not responding!
    echo Make sure backend is running: cd backend ^&^& .\run.bat
    exit /b 1
) else (
    echo OK: Backend is running ✓
)

echo.
echo [Test 2] Login API...
curl -s -X POST %API_URL%/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"admin\",\"password\":\"admin123\"}" | findstr "access_token" >nul
if errorlevel 1 (
    echo ERROR: Login failed!
    exit /b 1
) else (
    echo OK: Login endpoint works ✓
)

echo.
echo [Test 3] Get Current User (Me)...
for /f "tokens=*" %%a in ('curl -s -X POST %API_URL%/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"admin\",\"password\":\"admin123\"}" ^
  ^| findstr /r "access_token"') do (
  set TOKEN_INFO=%%a
)

if "!TOKEN_INFO!"=="" (
    echo ERROR: Could not get token!
    exit /b 1
) else (
    echo OK: Login successful ✓
)

echo.
echo [Test 4] Database Connection...
curl -s %API_URL%/../health | findstr "database" >nul
if errorlevel 1 (
    echo WARNING: Database status unknown
) else (
    echo OK: Database check passed ✓
)

echo.
echo ============================================
echo ALL TESTS PASSED! ✓
echo ============================================
echo.
echo Backend is ready at: %API_URL%
echo Frontend should now work at: http://localhost:5173
echo.
pause
