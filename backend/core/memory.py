"""Conversation memory — SQLite-backed chat history per session."""
import sqlite3
import json
import time
import uuid
from pathlib import Path
from backend.config import Config


class Memory:
    def __init__(self, db_path: Path = None):
        self.db = sqlite3.connect(
            db_path or (Config.DB_DIR / "chat_history.db"),
            check_same_thread=False,
        )
        self._init()

    def _init(self):
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created REAL,
            title TEXT,
            meta TEXT
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            ts REAL,
            role TEXT,
            content TEXT,
            provider TEXT,
            model TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        );
        CREATE INDEX IF NOT EXISTS idx_msg_session ON messages(session_id, ts);
        """)
        self.db.commit()

    def new_session(self, title: str = "New chat", meta: dict = None) -> str:
        sid = str(uuid.uuid4())
        self.db.execute(
            "INSERT INTO sessions (id, created, title, meta) VALUES (?, ?, ?, ?)",
            (sid, time.time(), title, json.dumps(meta or {}))
        )
        self.db.commit()
        return sid

    def add(self, session_id: str, role: str, content: str,
            provider: str = None, model: str = None):
        self.db.execute(
            "INSERT INTO messages (session_id, ts, role, content, provider, model) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, time.time(), role, content, provider, model)
        )
        self.db.commit()

    def history(self, session_id: str, limit: int = 50) -> list:
        cur = self.db.execute(
            "SELECT role, content FROM messages WHERE session_id=? ORDER BY ts DESC LIMIT ?",
            (session_id, limit)
        )
        rows = list(reversed(cur.fetchall()))
        return [{"role": r[0], "content": r[1]} for r in rows]

    def list_sessions(self, limit: int = 50) -> list:
        cur = self.db.execute(
            "SELECT id, created, title FROM sessions ORDER BY created DESC LIMIT ?",
            (limit,)
        )
        return [{"id": r[0], "created": r[1], "title": r[2]} for r in cur.fetchall()]


memory = Memory()
