"""
Response cache — saves LLM + intel API responses to SQLite, keyed by hash.
Reduces cost and speeds up repeat queries.
"""
import sqlite3
import hashlib
import json
import time
from backend.config import Config


_db = sqlite3.connect(Config.DB_DIR / "cache.db", check_same_thread=False)
_db.execute("""
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    namespace TEXT,
    value TEXT,
    ts REAL,
    expires REAL
);
""")
_db.execute("CREATE INDEX IF NOT EXISTS idx_cache_ns ON cache(namespace);")
_db.commit()


def _hash(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def get(namespace: str, *parts):
    key = _hash(namespace, *parts)
    cur = _db.execute("SELECT value, expires FROM cache WHERE key=?", (key,))
    row = cur.fetchone()
    if not row:
        return None
    value, expires = row
    if expires and time.time() > expires:
        _db.execute("DELETE FROM cache WHERE key=?", (key,))
        _db.commit()
        return None
    return json.loads(value)


def set_(namespace: str, value, *parts, ttl: int = 3600):
    key = _hash(namespace, *parts)
    expires = time.time() + ttl if ttl else None
    _db.execute(
        "INSERT OR REPLACE INTO cache (key, namespace, value, ts, expires) VALUES (?, ?, ?, ?, ?)",
        (key, namespace, json.dumps(value, default=str), time.time(), expires)
    )
    _db.commit()


def invalidate(namespace: str = None):
    if namespace:
        _db.execute("DELETE FROM cache WHERE namespace=?", (namespace,))
    else:
        _db.execute("DELETE FROM cache")
    _db.commit()


def stats() -> dict:
    cur = _db.execute("SELECT namespace, COUNT(*) FROM cache GROUP BY namespace")
    return {ns: count for ns, count in cur.fetchall()}
