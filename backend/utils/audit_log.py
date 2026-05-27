"""Immutable audit log — every action persisted append-only."""
import json
import time
import sqlite3
from backend.config import Config


_db = sqlite3.connect(Config.DB_DIR / "audit.db", check_same_thread=False)
_db.execute("""
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    event TEXT NOT NULL,
    actor TEXT,
    payload TEXT
);
""")
_db.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts DESC);")
_db.commit()


def audit(event: str, payload: dict = None, actor: str = "system") -> int:
    """Append an audit entry. Returns row id."""
    cur = _db.execute(
        "INSERT INTO audit_log (ts, event, actor, payload) VALUES (?, ?, ?, ?)",
        (time.time(), event, actor, json.dumps(payload or {}, default=str))
    )
    _db.commit()
    return cur.lastrowid


def recent(limit: int = 100, event_prefix: str = None) -> list:
    if event_prefix:
        cur = _db.execute(
            "SELECT ts, event, actor, payload FROM audit_log WHERE event LIKE ? ORDER BY ts DESC LIMIT ?",
            (event_prefix + "%", limit)
        )
    else:
        cur = _db.execute(
            "SELECT ts, event, actor, payload FROM audit_log ORDER BY ts DESC LIMIT ?",
            (limit,)
        )
    return [
        {"ts": r[0], "event": r[1], "actor": r[2], "payload": json.loads(r[3])}
        for r in cur.fetchall()
    ]
