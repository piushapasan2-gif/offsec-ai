"""Auth middleware - @require_auth decorator verifies Supabase JWT."""
import functools
from flask import request, jsonify, g
from backend.db.supabase_client import get_client, is_configured
from backend.config import Config


# In-memory cache: jwt -> user info (short TTL to avoid hammering Supabase Auth)
import time
_cache = {}
_CACHE_TTL = 300  # 5 minutes


def _extract_token():
    h = request.headers.get("Authorization", "")
    if h.startswith("Bearer "):
        return h[7:]
    # Allow ?token= for SSE/Socket.IO upgrade
    return request.args.get("token")


def verify(jwt: str) -> dict:
    """Verify JWT with Supabase. Returns user dict. Raises if invalid."""
    now = time.time()
    entry = _cache.get(jwt)
    if entry and entry[1] > now:
        return entry[0]
    user = get_client().verify_jwt(jwt)
    _cache[jwt] = (user, now + _CACHE_TTL)
    # Trim cache
    if len(_cache) > 500:
        for k in [k for k, v in _cache.items() if v[1] < now]:
            _cache.pop(k, None)
    return user


def require_auth(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        # Dev mode escape hatch: AUTH_DISABLED=1 in env (don't use in prod!)
        if not Config.PROD and not is_configured():
            g.user_id = "local-dev"
            g.user = {"id": "local-dev", "email": "dev@local"}
            return fn(*args, **kwargs)
        token = _extract_token()
        if not token:
            return jsonify({"ok": False, "error": "missing token"}), 401
        try:
            user = verify(token)
        except Exception as e:
            return jsonify({"ok": False, "error": f"invalid token: {e}"}), 401
        g.user = user
        g.user_id = user.get("id")
        return fn(*args, **kwargs)
    return wrapper


def current_user_id():
    return getattr(g, "user_id", None)
