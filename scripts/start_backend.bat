@echo off
setlocal

cd /d "%~dp0..\backend_v3"

set PYTHON_EXE=python
if exist ".venv-py312\Scripts\python.exe" (
    set PYTHON_EXE=.venv-py312\Scripts\python.exe
)

echo Starting Smart Parking API V3...
%PYTHON_EXE% -m app.main

pause
