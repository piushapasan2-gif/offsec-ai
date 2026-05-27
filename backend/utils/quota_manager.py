"""
Per-provider quota tracking — prevents blowing through free tiers.
Tracks request count + reset window per API.
"""
import sqlite3
import time
from backend.config import Config


_db = sqlite3.connect(Config.DB_DIR / "quotas.db", check_same_thread=False)
_db.execute("""
CREATE TABLE IF NOT EXISTS quota (
    provider TEXT PRIMARY KEY,
    count INTEGER DEFAULT 0,
    window_start REAL,
    window_seconds INTEGER,
    limit_per_window INTEGER
);
""")
_db.commit()


# Default free-tier limits (per day unless noted)
LIMITS = {
    "openai":      {"limit": 10000, "window": 86400},
    "anthropic":   {"limit":  1000, "window": 86400},
    "google":      {"limit":  1500, "window": 86400},
    "groq":        {"limit": 14400, "window": 86400},
    "deepseek":    {"limit": 10000, "window": 86400},
    "mistral":     {"limit":  1000, "window": 86400},
    "openrouter":  {"limit":   200, "window": 86400},
    "huggingface": {"limit":  1000, "window": 86400},
    "together":    {"limit":   100, "window": 86400},
    "cohere":      {"limit":  1000, "window": 86400},
    "perplexity":  {"limit":   200, "window": 86400},
    "xai":         {"limit":   500, "window": 86400},
    "shodan":      {"limit":   100, "window": 2592000},  # monthly
    "censys":      {"limit":   250, "window": 2592000},
    "virustotal":  {"limit":   500, "window": 86400},
    "abuseipdb":   {"limit":  1000, "window": 86400},
    "urlscan":     {"limit":   100, "window": 86400},
    "ipinfo":      {"limit": 50000, "window": 2592000},
}


def check(provider: str) -> tuple:
    """Returns (allowed, count, limit). Doesn't increment."""
    limits = LIMITS.get(provider, {"limit": 999999, "window": 86400})
    now = time.time()
    cur = _db.execute("SELECT count, window_start FROM quota WHERE provider=?", (provider,))
    row = cur.fetchone()
    if not row:
        return True, 0, limits["limit"]
    count, ws = row
    if now - ws > limits["window"]:
        # Window expired
        return True, 0, limits["limit"]
    return count < limits["limit"], count, limits["limit"]


def consume(provider: str, n: int = 1) -> bool:
    """Increment usage. Returns True if within limit."""
    limits = LIMITS.get(provider, {"limit": 999999, "window": 86400})
    now = time.time()
    cur = _db.execute("SELECT count, window_start FROM quota WHERE provider=?", (provider,))
    row = cur.fetchone()
    if not row:
        _db.execute(
            "INSERT INTO quota (provider, count, window_start, window_seconds, limit_per_window) VALUES (?, ?, ?, ?, ?)",
            (provider, n, now, limits["window"], limits["limit"])
        )
        _db.commit()
        return True
    count, ws = row
    if now - ws > limits["window"]:
        # Reset window
        _db.execute("UPDATE quota SET count=?, window_start=? WHERE provider=?", (n, now, provider))
    else:
        _db.execute("UPDATE quota SET count=count+? WHERE provider=?", (n, provider))
    _db.commit()
    allowed, count, limit = check(provider)
    return allowed


def status() -> dict:
    cur = _db.execute("SELECT provider, count, window_start, window_seconds, limit_per_window FROM quota")
    now = time.time()
    out = {}
    for p, c, ws, w, lim in cur.fetchall():
        out[p] = {
            "used": c if (now - ws) <= w else 0,
            "limit": lim,
            "resets_in": max(0, int(ws + w - now)),
        }
    return out
