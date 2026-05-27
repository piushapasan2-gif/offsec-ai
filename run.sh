#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║       OffSec AI 2025 — Booting...            ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""

PY=$(command -v python3 || command -v python)
[ -z "$PY" ] && { echo "[!] Python not found"; exit 1; }

[ ! -d ".venv" ] && { echo "[*] Creating venv..."; $PY -m venv .venv; }
source .venv/bin/activate

echo "[*] Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo ""
echo "  [+] Dashboard:  http://127.0.0.1:7777"
echo "  [+] Ctrl+C to stop"
echo ""
(sleep 1 && (xdg-open http://127.0.0.1:7777 2>/dev/null || open http://127.0.0.1:7777 2>/dev/null)) &
python run.py
