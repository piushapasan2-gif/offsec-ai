"""WSGI entry point for gunicorn / Render.

Note: do NOT call eventlet.monkey_patch() here.
Gunicorn's --worker-class eventlet performs the patch inside each worker.
Double-patching from wsgi.py causes the worker to exit with status 1.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.app import app, socketio  # noqa: E402

__all__ = ["app", "socketio"]
