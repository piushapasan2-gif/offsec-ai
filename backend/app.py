"""OffSec AI 2025 - Flask app + Socket.IO with Supabase auth."""
import os
from flask import Flask, request, jsonify, send_from_directory, g
from flask_socketio import SocketIO, emit, disconnect

from backend.config import Config
from backend.core import router, scope_guard
from backend.core import orchestrator
from backend.db.repo import chat_repo, audit_repo, findings_repo
from backend.auth.middleware import require_auth, verify, current_user_id
from backend.utils import quota_manager
from backend.utils.logger import get_logger

log = get_logger("app")
FRONTEND_DIR = Config.BASE_DIR / "frontend"

app = Flask(
    __name__,
    static_folder=str(FRONTEND_DIR),
    static_url_path="/static",
)
app.config["SECRET_KEY"] = Config.SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


# --- Static frontend ---
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/login")
def login_page():
    return send_from_directory(FRONTEND_DIR, "login.html")


@app.route("/css/<path:fname>")
def css(fname): return send_from_directory(FRONTEND_DIR / "css", fname)


@app.route("/js/<path:fname>")
def js(fname): return send_from_directory(FRONTEND_DIR / "js", fname)


# --- Health & auth config ---
@app.route("/health")
def health():
    return jsonify({"ok": True, "service": "offsec-ai", "version": "2025.2"})


@app.route("/api/auth/config")
def auth_config():
    return jsonify({
        "url": Config.SUPABASE_URL,
        "anon_key": Config.SUPABASE_ANON_KEY,
        "configured": bool(Config.SUPABASE_URL and Config.SUPABASE_ANON_KEY),
    })


@app.route("/api/auth/me")
@require_auth
def me():
    return jsonify({"ok": True, "user": g.user})


# --- Chat ---
@app.route("/api/chat", methods=["POST"])
@require_auth
def api_chat():
    data = request.get_json(force=True)
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"ok": False, "error": "empty prompt"}), 400
    result = orchestrator.handle(
        prompt,
        user_id=current_user_id(),
        session_id=data.get("session_id"),
        prefer=data.get("prefer"),
        target=data.get("target"),
    )
    return jsonify(result)



# --- Streaming chat ---
@app.route("/api/chat/stream", methods=["POST"])
@require_auth
def api_chat_stream():
    import json as _json
    from flask import Response, stream_with_context
    data = request.get_json(force=True)
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"ok": False, "error": "empty prompt"}), 400

    uid = current_user_id()
    sid = data.get("session_id")
    prefer = data.get("prefer")
    target = data.get("target")

    def generate():
        try:
            for chunk in orchestrator.handle_stream(prompt, user_id=uid,
                                                    session_id=sid, prefer=prefer, target=target):
                yield f"data: {_json.dumps(chunk)}\n\n"
        except Exception as e:
            yield f"data: {_json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/sessions")
@require_auth
def api_sessions():
    return jsonify(chat_repo.list_sessions(current_user_id()))


@app.route("/api/sessions/<sid>")
@require_auth
def api_session(sid):
    return jsonify({"id": sid, "messages": chat_repo.history(sid, current_user_id(), limit=200)})


# --- LLM ---
@app.route("/api/llm/status")
@require_auth
def api_llm_status():
    from backend.core.ai_engine import PROVIDERS
    return jsonify({
        "configured": list(PROVIDERS.keys()),
        "all_keys": {k: bool(v) for k, v in Config.LLM_KEYS.items()},
    })


@app.route("/api/llm/healthcheck", methods=["POST"])
@require_auth
def api_llm_health():
    return jsonify(router.health_check())


# --- Intel ---
@app.route("/api/intel/status")
@require_auth
def api_intel_status():
    # Map config key names to provider names used in INTEL_MAP
    KEY_ALIAS = {"nvd": "cve"}
    status = {}
    for k, v in Config.INTEL_KEYS.items():
        alias = KEY_ALIAS.get(k, k)
        status[alias] = bool(v)
    status["github"] = bool(Config.GITHUB_TOKEN)
    return jsonify(status)


INTEL_MAP = {
    "shodan":     ("shodan_intel",    {"host":"host_info","search":"search","info":"api_info","myip":"my_ip"}),
    "virustotal": ("virustotal",      {"ip":"ip_info","domain":"domain_info","hash":"file_hash_info","url_scan":"url_scan"}),
    "otx":        ("otx",             {"ip":"ip_indicators","domain":"domain_indicators","hash":"file_hash_indicators","pulses":"pulses"}),
    "abuseipdb":  ("abuseipdb",       {"check":"check_ip"}),
    "urlscan":    ("urlscan",         {"submit":"submit","result":"result","search":"search"}),
    "ipinfo":     ("ipinfo",          {"lookup":"lookup","myip":"my_ip"}),
    "cve":        ("cve_monitor",     {"lookup":"cve_lookup","search":"search","critical":"critical_recent"}),
    "github":     ("github_intel",    {"code":"code_search","repo":"repo_search","commits":"commits_search","org":"org_recon"}),
    "fullhunt":   ("fullhunt",        {"domain":"domain_details","subdomains":"subdomains"}),
    "leakix":     ("leakix",          {"host":"host_lookup","search":"search"}),
}


@app.route("/api/intel/<provider>", methods=["POST"])
@require_auth
def api_intel_call(provider):
    data = request.get_json(force=True) or {}
    action = data.get("action", "lookup")
    args = data.get("args", {})
    if provider not in INTEL_MAP:
        return jsonify({"ok": False, "error": f"unknown provider {provider}"}), 400
    module_name, actions = INTEL_MAP[provider]
    if action not in actions:
        return jsonify({"ok": False, "error": f"unknown action {action}"}), 400
    try:
        import importlib
        m = importlib.import_module(f"backend.intelligence.{module_name}")
        fn = getattr(m, actions[action])
        result = fn(**args) if isinstance(args, dict) else fn(args)
        audit_repo.log(f"intel.{provider}.{action}", {"args": args}, user_id=current_user_id())
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500



# --- Intel bulk scan ---
@app.route("/api/intel/bulk", methods=["POST"])
@require_auth
def api_intel_bulk():
    import re, importlib, ipaddress
    from concurrent.futures import ThreadPoolExecutor, as_completed

    data = request.get_json(force=True) or {}
    target = (data.get("target") or "").strip()
    if not target:
        return jsonify({"ok": False, "error": "target required"}), 400

    # Detect target type
    def is_ip(t):
        try: ipaddress.ip_address(t); return True
        except: return False
    def is_hash(t):
        return bool(re.match(r'^[0-9a-fA-F]{32,64}$', t))

    if is_ip(target):
        target_type = "ip"
        tasks = {
            "shodan":     ("shodan_intel",  "host_info",           {"ip": target}),
            "virustotal": ("virustotal",    "ip_info",             {"ip": target}),
            "abuseipdb":  ("abuseipdb",     "check_ip",            {"ip": target}),
            "ipinfo":     ("ipinfo",        "lookup",              {"ip": target}),
            "otx":        ("otx",           "ip_indicators",       {"ip": target}),
        }
    elif is_hash(target):
        target_type = "hash"
        tasks = {
            "virustotal": ("virustotal",    "file_hash_info",      {"hash_": target}),
            "otx":        ("otx",           "file_hash_indicators",{"hash_": target}),
        }
    else:
        target_type = "domain"
        tasks = {
            "virustotal": ("virustotal",    "domain_info",         {"domain": target}),
            "otx":        ("otx",           "domain_indicators",   {"domain": target}),
            "urlscan":    ("urlscan",       "search",              {"query": target}),
            "fullhunt":   ("fullhunt",      "domain_details",      {"domain": target}),
            "leakix":     ("leakix",        "search",              {"query": target}),
        }

    # Key availability map
    key_map = {
        "shodan": bool(Config.INTEL_KEYS.get("shodan")),
        "virustotal": bool(Config.INTEL_KEYS.get("virustotal")),
        "abuseipdb": bool(Config.INTEL_KEYS.get("abuseipdb")),
        "ipinfo": bool(Config.INTEL_KEYS.get("ipinfo")),
        "otx": bool(Config.INTEL_KEYS.get("otx")),
        "urlscan": bool(Config.INTEL_KEYS.get("urlscan")),
        "fullhunt": bool(Config.INTEL_KEYS.get("fullhunt")),
        "leakix": bool(Config.INTEL_KEYS.get("leakix")),
    }
    active = {k: v for k, v in tasks.items() if key_map.get(k, False)}

    def run_one(name, module_name, fn_name, args):
        try:
            m = importlib.import_module(f"backend.intelligence.{module_name}")
            result = getattr(m, fn_name)(**args)
            return name, {"ok": True, "data": result}
        except Exception as e:
            return name, {"ok": False, "error": str(e)}

    results = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(run_one, n, mod, fn, args): n
                   for n, (mod, fn, args) in active.items()}
        for future in as_completed(futures, timeout=30):
            name, res = future.result()
            results[name] = res

    audit_repo.log("intel.bulk", {"target": target, "type": target_type,
                                   "providers": list(results.keys())},
                   user_id=current_user_id())
    return jsonify({"ok": True, "target": target, "type": target_type, "results": results})


# --- Intel history (last 50 intel audit events) ---
@app.route("/api/intel/history")
@require_auth
def api_intel_history():
    rows = audit_repo.recent(current_user_id(), limit=50, prefix="intel.")
    return jsonify(rows)


# --- Scope ---
@app.route("/api/scope", methods=["GET", "POST"])
@require_auth
def api_scope():
    if request.method == "POST":
        data = request.get_json(force=True)
        if "engagement" in data:
            scope_guard.set_engagement(
                data["engagement"], data.get("in_scope", []), data.get("blocklist", [])
            )
        if "mode" in data:
            scope_guard.set_mode(data["mode"])
        audit_repo.log("scope.changed", data, user_id=current_user_id())
    return jsonify(scope_guard.current_scope())


# --- Audit & Quotas ---
@app.route("/api/audit")
@require_auth
def api_audit():
    return jsonify(audit_repo.recent(current_user_id(), limit=200,
                                     prefix=request.args.get("prefix")))


@app.route("/api/quotas")
@require_auth
def api_quotas():
    return jsonify(quota_manager.status())


# --- Findings ---
@app.route("/api/findings", methods=["GET", "POST"])
@require_auth
def api_findings():
    uid = current_user_id()
    if request.method == "POST":
        d = request.get_json(force=True)
        r = findings_repo.add(
            user_id=uid,
            title=d["title"], severity=d.get("severity", "info"),
            description=d.get("description"), evidence=d.get("evidence"),
            engagement=d.get("engagement"), cvss=d.get("cvss"),
            cve_ids=d.get("cve_ids"), mitre=d.get("mitre"),
        )
        return jsonify({"ok": True, "data": r})
    return jsonify(findings_repo.list(uid,
                                      status=request.args.get("status"),
                                      severity=request.args.get("severity")))


# --- Socket.IO ---
@socketio.on("connect")
def on_connect(auth=None):
    token = (auth or {}).get("token") if isinstance(auth, dict) else None
    if not token:
        token = request.args.get("token")
    try:
        if token:
            user = verify(token)
            emit("log", {"msg": f"Connected as {user.get('email')}", "level": "success"})
        elif not Config.PROD:
            emit("log", {"msg": "Connected (dev)", "level": "info"})
        else:
            disconnect()
    except Exception:
        disconnect()


from werkzeug.exceptions import HTTPException


@app.errorhandler(HTTPException)
def handle_http_error(e):
    return jsonify({"ok": False, "error": e.description, "code": e.code}), e.code


@app.errorhandler(Exception)
def handle_error(e):
    log.exception(e)
    if Config.PROD:
        return jsonify({"ok": False, "error": "internal error"}), 500
    return jsonify({"ok": False, "error": str(e), "type": type(e).__name__}), 500
