#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  OffSec AI 2025 — Kali Linux Installer
#  Usage:  curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/offsec-ai/main/install.sh | bash
#  Or:     chmod +x install.sh && ./install.sh
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
INSTALL_DIR="/opt/offsec-ai"
REPO="https://github.com/YOUR_USERNAME/offsec-ai.git"
SERVICE_USER="$USER"

banner() {
  echo -e "${CYAN}"
  echo "╔══════════════════════════════════════════════╗"
  echo "║   OffSec AI 2025 — Kali Installer            ║"
  echo "║   Multi-LLM · Multi-Agent · Authorized Use   ║"
  echo "╚══════════════════════════════════════════════╝"
  echo -e "${NC}"
}

info()    { echo -e "${GREEN}[*]${NC} $*"; }
warn()    { echo -e "${RED}[!]${NC} $*"; }
success() { echo -e "${GREEN}[✔]${NC} $*"; }

banner

# ── Root check ──────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
  warn "Run as root or with sudo for system-wide install."
  warn "Continuing as current user — install dir: $HOME/.local/offsec-ai"
  INSTALL_DIR="$HOME/.local/offsec-ai"
fi

# ── Dependencies ─────────────────────────────────────────────────
info "Updating package list and installing dependencies..."
apt-get update -qq
apt-get install -y --no-install-recommends \
  python3 python3-pip python3-venv git curl wget build-essential \
  libssl-dev libffi-dev 2>/dev/null | grep -E "^(Get|Inst|Remov)" || true
success "Dependencies installed"

# ── Clone or update ──────────────────────────────────────────────
if [[ -d "$INSTALL_DIR/.git" ]]; then
  info "Existing install found — pulling latest..."
  git -C "$INSTALL_DIR" pull --ff-only
else
  info "Cloning OffSec AI into $INSTALL_DIR..."
  git clone "$REPO" "$INSTALL_DIR"
fi
success "Code ready at $INSTALL_DIR"

# ── Virtual environment ──────────────────────────────────────────
info "Setting up Python virtual environment..."
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
success "Python environment ready"

# ── .env setup ───────────────────────────────────────────────────
if [[ ! -f "$INSTALL_DIR/.env" ]]; then
  cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
  warn ".env created from template — edit it with your API keys:"
  warn "  nano $INSTALL_DIR/.env"
else
  info ".env already exists — skipping"
fi

# ── Optional: systemd service ─────────────────────────────────────
if [[ $EUID -eq 0 ]] && command -v systemctl &>/dev/null; then
  info "Installing systemd service..."
  cat > /etc/systemd/system/offsec-ai.service << SERVICE
[Unit]
Description=OffSec AI 2025
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/.venv/bin/gunicorn --worker-class gthread -w 1 --threads 4 --bind 127.0.0.1:7777 --timeout 120 wsgi:app
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SERVICE
  systemctl daemon-reload
  success "Systemd service installed (not started)"
  echo ""
  echo "  To start on boot:  sudo systemctl enable offsec-ai"
  echo "  To start now:      sudo systemctl start offsec-ai"
fi

# ── Done ─────────────────────────────────────────────────────────
echo ""
success "OffSec AI 2025 installed!"
echo ""
echo "  1. Edit API keys:  nano $INSTALL_DIR/.env"
echo "  2. Run:            cd $INSTALL_DIR && ./run.sh"
echo "  3. Open:           http://127.0.0.1:7777"
echo ""
