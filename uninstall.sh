#!/usr/bin/env bash
# OffSec AI 2025 — Uninstaller
set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; NC='\033[0m'

INSTALL_DIR="/opt/offsec-ai"
[[ -d "$HOME/.local/offsec-ai" ]] && INSTALL_DIR="$HOME/.local/offsec-ai"

echo -e "${RED}[!]${NC} This will remove OffSec AI from $INSTALL_DIR"
read -rp "Continue? [y/N] " confirm
[[ "${confirm,,}" != "y" ]] && echo "Aborted." && exit 0

# Stop & remove systemd service
if systemctl is-active --quiet offsec-ai 2>/dev/null; then
  sudo systemctl stop offsec-ai
  sudo systemctl disable offsec-ai
  sudo rm -f /etc/systemd/system/offsec-ai.service
  sudo systemctl daemon-reload
  echo -e "${GREEN}[✔]${NC} Service removed"
fi

# Remove install directory
rm -rf "$INSTALL_DIR"
echo -e "${GREEN}[✔]${NC} Removed $INSTALL_DIR"
echo "OffSec AI 2025 uninstalled."
