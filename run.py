"""OffSec AI 2025 — main entry point."""
import sys
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.app import app, socketio
from backend.config import Config


def banner():
    print(r"""
    ╔══════════════════════════════════════════════════════════╗
    ║   ___   __  __ _____           _    ___    ____          ║
    ║  / _ \ / _|/ _/ ___|  ___  ___/ \  |_ _|  |___ \         ║
    ║ | | | | |_| |_\___ \ / _ \/ __/ _ \  | |    __) |        ║
    ║ | |_| |  _|  _|___) |  __/ (_/ ___ \ | |   / __/         ║
    ║  \___/|_| |_| |____/ \___|\___/_/  \_|___| |_____|       ║
    ║                                                          ║
    ║         Elite Offensive Security Suite  v2025.2          ║
    ║         Multi-LLM · Multi-Agent · Authorized Use         ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    llms = Config.available_llms()
    intel = Config.available_intel()
    print(f"   ▶ LLM providers:  {len(llms)}/12 active  →  {', '.join(llms) or 'NONE'}")
    print(f"   ▶ Intel APIs:     {len(intel)}/17 active")
    print(f"   ▶ Dashboard:      http://{Config.HOST}:{Config.PORT}")
    print(f"   ▶ Logs:           {Config.LOG_DIR}")
    print()


if __name__ == "__main__":
    banner()
    socketio.run(app, host=Config.HOST, port=Config.PORT,
                 debug=False, allow_unsafe_werkzeug=True)
