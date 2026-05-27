"""WSGI entry point for gunicorn / Render."""
import sys
from pathlib import Path

# eventlet must be patched before anything else for Socket.IO
import eventlet
eventlet.monkey_patch()

sys.path.insert(0, str(Path(__file__).parent))

from backend.app import app, socketio  # noqa: E402

# gunicorn looks for `app` by default
__all__ = ["app", "socketio"]
