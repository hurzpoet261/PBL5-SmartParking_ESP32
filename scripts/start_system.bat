@echo off
start "Smart Parking Backend" cmd /k "cd /d %~dp0..\backend && python app.py"
timeout /t 3 /nobreak
start "" "%~dp0..\web\index.html"
echo.
echo ✅ System started!
echo    Backend: http://localhost:8000
echo    Web: Opened in browser
pause
