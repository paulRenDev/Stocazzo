@echo off
REM Starts the DJI Mapping Mission Builder web UI. Double-click this file
REM from the dji_mission_builder folder.
cd /d "%~dp0"

echo Installing dependencies (Flask, pytest)...
python -m pip install --quiet -r requirements.txt

echo Starting DJI Mapping Mission Builder...
echo Your browser should open automatically. If not, go to http://127.0.0.1:5000
python app\server.py

pause
