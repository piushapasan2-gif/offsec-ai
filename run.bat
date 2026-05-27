@echo off
title OffSec AI 2025

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║       OffSec AI 2025 — Booting...            ║
echo  ╚══════════════════════════════════════════════╝
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [!] Python not found. Install Python 3.10+ from python.org
    pause
    exit /b 1
)

cd /d "%~dp0"

if not exist ".venv\" (
    echo [*] Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [*] Installing dependencies (first run may take 2-3 minutes)...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo.
echo  [+] Dashboard:  http://127.0.0.1:7777
echo  [+] Ctrl+C to stop
echo.
start "" "http://127.0.0.1:7777"

python run.py
pause
