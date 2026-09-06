#!/usr/bin/env bash
# Starts the DJI Mapping Mission Builder web UI. Double-click this file
# (or run `./run.sh` in a terminal) from the dji_mission_builder folder.
set -e
cd "$(dirname "$0")"

PYTHON=python3
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON=python

echo "Installing dependencies (Flask, pytest)..."
"$PYTHON" -m pip install --quiet -r requirements.txt

echo "Starting DJI Mapping Mission Builder..."
echo "Your browser should open automatically. If not, go to http://127.0.0.1:5000"
"$PYTHON" app/server.py
