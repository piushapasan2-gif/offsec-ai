"""
Scope Guard — enforces in-scope-only enforcement.

Reads scope rules from database/scope.json per engagement.
Blocks actions against hosts/IPs/domains not in scope.

Supports:
  - Exact host (target.com)
  - Wildcard subdomains (*.target.com)
  - CIDR (10.0.0.0/24)
  - Block lists (never-touch)
"""
import json
import ipaddress
import re
from pathlib import Path
from backend.config import Config


SCOPE_FILE = Config.DB_DIR / "scope.json"

# Always blocked — never touch these regardless of scope
BLOCKLIST = {
    # Real-world critical infrastructure that should never be targeted
    "168.0.0.1", "127.0.0.1", "localhost",
    # Anthropic / OpenAI / Google etc — your own LLM providers
    "api.anthropic.com", "api.openai.com", "generativelanguage.googleapis.com",
}


def _load_scope() -> dict:
    if not SCOPE_FILE.exists():
        # Default empty scope == permissive (lab mode)
        return {"mode": "permissive", "engagements": {}, "current": None}
    return json.loads(SCOPE_FILE.read_text())


def _save_scope(scope: dict):
    SCOPE_FILE.write_text(json.dumps(scope, indent=2))


def set_engagement(name: str, in_scope: list, blocklist: list = None):
    """Define an engagement and its scope."""
    scope = _load_scope()
    scope["engagements"][name] = {
        "in_scope": in_scope or [],
        "blocklist": blocklist or [],
    }
    scope["current"] = name
    scope["mode"] = "strict"
    _save_scope(scope)


def set_mode(mode: str):
    """mode = 'strict' | 'permissive' | 'lab'"""
    scope = _load_scope()
    scope["mode"] = mode
    _save_scope(scope)


def _match(target: str, rule: str) -> bool:
    target = target.lower().strip()
    rule = rule.lower().strip()
    # CIDR
    if "/" in rule:
        try:
            net = ipaddress.ip_network(rule, strict=False)
            return ipaddress.ip_address(target) in net
        except ValueError:
            return False
    # Wildcard
    if rule.startswith("*."):
        base = rule[2:]
        return target == base or target.endswith("." + base)
    # Exact
    return target == rule


def enforce_scope(target: str, session_id: str = None) -> tuple:
    """
    Returns (allowed: bool, reason: str)
    """
    if not target:
        return True, "no target"

    target = target.strip().lower()
    scope = _load_scope()

    # Always-blocked
    for blocked in BLOCKLIST:
        if _match(target, blocked):
            return False, f"target matches global blocklist ({blocked})"

    mode = scope.get("mode", "permissive")
    if mode == "permissive":
        return True, "permissive mode"
    if mode == "lab":
        # Only allow private IP ranges
        try:
            ip = ipaddress.ip_address(target)
            if ip.is_private or ip.is_loopback:
                return True, "lab mode: private IP"
            return False, "lab mode: only private IPs allowed"
        except ValueError:
            # Hostname — allow .local, .lab, .test
            if any(target.endswith(s) for s in (".local", ".lab", ".test", ".htb", ".thm")):
                return True, "lab mode: lab TLD"
            return False, "lab mode: only private/lab targets allowed"

    # Strict mode — must match current engagement
    cur = scope.get("current")
    if not cur:
        return False, "strict mode but no current engagement set"
    eng = scope["engagements"].get(cur, {})
    for rule in eng.get("blocklist", []):
        if _match(target, rule):
            return False, f"engagement blocklist ({rule})"
    for rule in eng.get("in_scope", []):
        if _match(target, rule):
            return True, f"matches scope rule ({rule})"
    return False, f"not in engagement scope '{cur}'"


def current_scope() -> dict:
    return _load_scope()
