@echo off
setlocal

set MOSQUITTO_EXE=C:\Program Files\Mosquitto\mosquitto.exe
set CONF=%~dp0mosquitto_pbl5.conf

if not exist "%MOSQUITTO_EXE%" (
    echo ERROR: Mosquitto not found: %MOSQUITTO_EXE%
    pause
    exit /b 1
)

echo Starting PBL5 Mosquitto broker on 0.0.0.0:1883...
"%MOSQUITTO_EXE%" -c "%CONF%" -v

pause
