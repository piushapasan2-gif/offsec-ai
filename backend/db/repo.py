"""Storage repository - switches between Supabase and SQLite based on config."""
import sqlite3, json, time, uuid
from backend.config import Config
from backend.db.supabase_client import get_client, is_configured


def _use_supabase():
    return Config.STORAGE_BACKEND == "supabase" and is_configured()


# ===========================================================
#  Chat (sessions + messages)
# ===========================================================
class ChatRepo:
    def __init__(self):
        if not _use_supabase():
            db_path = Config.DB_DIR / "chat_v2.db"
            self.db = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
            self.db.execute("""CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, user_id TEXT, created REAL, title TEXT, meta TEXT)""")
            self.db.execute("""CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, user_id TEXT,
                ts REAL, role TEXT, content TEXT, provider TEXT, model TEXT, elapsed_ms INTEGER)""")
            self.db.execute("CREATE INDEX IF NOT EXISTS idx_msg_session ON messages(session_id, ts)")

    def new_session(self, user_id, title="New chat", meta=None):
        if _use_supabase():
            r = get_client().insert("chat_sessions", {
                "user_id": user_id, "title": title, "meta": meta or {}
            })
            return r[0]["id"] if r else None
        sid = str(uuid.uuid4())
        self.db.execute(
            "INSERT INTO sessions (id, user_id, created, title, meta) VALUES (?, ?, ?, ?, ?)",
            (sid, user_id, time.time(), title, json.dumps(meta or {}))
        )
        return sid

    def add(self, session_id, user_id, role, content, provider=None, model=None, elapsed_ms=None):
        if _use_supabase():
            return get_client().insert("chat_messages", {
                "session_id": session_id, "user_id": user_id, "role": role,
                "content": content, "provider": provider, "model": model,
                "elapsed_ms": elapsed_ms,
            })
        self.db.execute(
            "INSERT INTO messages (session_id, user_id, ts, role, content, provider, model, elapsed_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, user_id, time.time(), role, content, provider, model, elapsed_ms)
        )

    def history(self, session_id, user_id, limit=50):
        if _use_supabase():
            rows = get_client().select("chat_messages",
                filters={"session_id": f"eq.{session_id}", "user_id": f"eq.{user_id}"},
                order="ts.asc", limit=limit)
            return [{"role": r["role"], "content": r["content"]} for r in (rows or [])]
        cur = self.db.execute(
            "SELECT role, content FROM messages WHERE session_id=? AND user_id=? ORDER BY ts ASC LIMIT ?",
            (session_id, user_id, limit)
        )
        return [{"role": r[0], "content": r[1]} for r in cur.fetchall()]

    def list_sessions(self, user_id, limit=50):
        if _use_supabase():
            rows = get_client().select("chat_sessions",
                filters={"user_id": f"eq.{user_id}"},
                order="created_at.desc", limit=limit)
            return [{"id": r["id"], "title": r["title"], "created": r["created_at"]} for r in (rows or [])]
        cur = self.db.execute(
            "SELECT id, created, title FROM sessions WHERE user_id=? ORDER BY created DESC LIMIT ?",
            (user_id, limit)
        )
        return [{"id": r[0], "created": r[1], "title": r[2]} for r in cur.fetchall()]


# ===========================================================
#  Audit
# ===========================================================
class AuditRepo:
    def __init__(self):
        if not _use_supabase():
            self.db = sqlite3.connect(str(Config.DB_DIR / "audit_v2.db"), check_same_thread=False, isolation_level=None)
            self.db.execute("""CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, event TEXT,
                actor TEXT, user_id TEXT, payload TEXT)""")

    def log(self, event, payload=None, user_id=None, actor="user"):
        if _use_supabase():
            return get_client().insert("audit_log", {
                "user_id": user_id, "event": event, "actor": actor,
                "payload": payload or {},
            })
        self.db.execute(
            "INSERT INTO audit_log (ts, event, actor, user_id, payload) VALUES (?, ?, ?, ?, ?)",
            (time.time(), event, actor, user_id, json.dumps(payload or {}, default=str))
        )

    def recent(self, user_id, limit=100, prefix=None):
        if _use_supabase():
            f = {"user_id": f"eq.{user_id}"}
            if prefix:
                f["event"] = f"like.{prefix}%"
            rows = get_client().select("audit_log", filters=f, order="ts.desc", limit=limit)
            return rows or []
        if prefix:
            cur = self.db.execute(
                "SELECT ts, event, actor, payload FROM audit_log WHERE user_id=? AND event LIKE ? ORDER BY ts DESC LIMIT ?",
                (user_id, prefix + "%", limit))
        else:
            cur = self.db.execute(
                "SELECT ts, event, actor, payload FROM audit_log WHERE user_id=? ORDER BY ts DESC LIMIT ?",
                (user_id, limit))
        return [{"ts": r[0], "event": r[1], "actor": r[2], "payload": json.loads(r[3])} for r in cur.fetchall()]


# ===========================================================
#  Findings
# ===========================================================
class FindingsRepo:
    def __init__(self):
        if not _use_supabase():
            self.db = sqlite3.connect(str(Config.DB_DIR / "findings_v2.db"), check_same_thread=False, isolation_level=None)
            self.db.execute("""CREATE TABLE IF NOT EXISTS findings (
                id TEXT PRIMARY KEY, user_id TEXT, engagement TEXT,
                severity TEXT, title TEXT, description TEXT,
                evidence TEXT, cvss REAL, cve_ids TEXT, mitre_tactics TEXT,
                status TEXT DEFAULT 'open', created_at REAL)""")
            self.db.execute("CREATE INDEX IF NOT EXISTS idx_findings_user ON findings(user_id, created_at DESC)")

    def add(self, user_id, title, severity, description=None, evidence=None,
            engagement=None, cvss=None, cve_ids=None, mitre=None):
        if _use_supabase():
            return get_client().insert("findings", {
                "user_id": user_id, "title": title, "severity": severity,
                "description": description, "evidence": evidence or {},
                "engagement": engagement, "cvss": cvss,
                "cve_ids": cve_ids or [], "mitre_tactics": mitre or [],
            })
        fid = str(uuid.uuid4())
        self.db.execute(
            "INSERT INTO findings (id, user_id, engagement, severity, title, description, "
            "evidence, cvss, cve_ids, mitre_tactics, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (fid, user_id, engagement, severity, title, description,
             json.dumps(evidence or {}), cvss,
             json.dumps(cve_ids or []), json.dumps(mitre or []),
             time.time())
        )
        return {"id": fid, "title": title, "severity": severity}

    def list(self, user_id, status=None, severity=None, limit=100):
        if _use_supabase():
            f = {"user_id": f"eq.{user_id}"}
            if status:   f["status"] = f"eq.{status}"
            if severity: f["severity"] = f"eq.{severity}"
            return get_client().select("findings", filters=f, order="created_at.desc", limit=limit) or []
        q = ("SELECT id, engagement, severity, title, description, cvss, "
             "cve_ids, mitre_tactics, status, created_at FROM findings WHERE user_id=?")
        params = [user_id]
        if status:   q += " AND status=?";   params.append(status)
        if severity: q += " AND severity=?"; params.append(severity)
        q += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = self.db.execute(q, params).fetchall()
        return [{"id": r[0], "engagement": r[1], "severity": r[2], "title": r[3],
                 "description": r[4], "cvss": r[5],
                 "cve_ids": json.loads(r[6] or "[]"),
                 "mitre_tactics": json.loads(r[7] or "[]"),
                 "status": r[8], "created_at": r[9]} for r in rows]


# --- Lazy singletons ---
_chat_repo = None
_audit_repo = None
_findings_repo = None


def _get_chat_repo():
    global _chat_repo
    if _chat_repo is None:
        _chat_repo = ChatRepo()
    return _chat_repo


def _get_audit_repo():
    global _audit_repo
    if _audit_repo is None:
        _audit_repo = AuditRepo()
    return _audit_repo


def _get_findings_repo():
    global _findings_repo
    if _findings_repo is None:
        _findings_repo = FindingsRepo()
    return _findings_repo


class _LazyProxy:
    """Proxy that defers repo creation until first use."""
    def __init__(self, factory):
        self._factory = factory

    def __getattr__(self, name):
        return getattr(self._factory(), name)


chat_repo = _LazyProxy(_get_chat_repo)
audit_repo = _LazyProxy(_get_audit_repo)
findings_repo = _LazyProxy(_get_findings_repo)
