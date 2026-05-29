@echo off
cd /d "%~dp0..\backend"
pip install -q -r requirements.txt
python app.py
pause
