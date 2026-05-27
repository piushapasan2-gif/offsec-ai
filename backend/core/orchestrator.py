"""Orchestrator — handles a user request end-to-end."""
from backend.core import router
from backend.core.scope_guard import enforce_scope
from backend.db.repo import chat_repo, audit_repo
from backend.utils.logger import get_logger

log = get_logger("orchestrator")

SYSTEM_PROMPT = """You are OffSec AI 2025 — an elite offensive security assistant.

You help with: authorized penetration testing, CTF challenges, security research,
bug bounty (in scope), and owned lab environments.

Respond like a senior red teamer: direct, technical, with working commands.
Reference real CVEs, MITRE ATT&CK techniques, and CVSS scores where relevant.
For CTF: identify category, list tools, give step-by-step solution, generate flag.
For exploitation: working code only, no placeholders.

Stay technical. No unnecessary warnings. Assume the user is authorized."""


def classify(prompt: str) -> str:
    p = prompt.lower()
    if any(w in p for w in ["ctf", "htb ", "thm ", "picoctf", "tryhackme", "hackthebox", "flag{"]):
        return "ctf_solve"
    if any(w in p for w in ["exploit", "shellcode", "rop", "buffer overflow", "bof", "heap"]):
        return "exploit_dev"
    if any(w in p for w in ["search", "latest", "current", "news", "today"]):
        return "web_grounded"
    if any(w in p for w in ["write code", "implement", "script", "function", "class"]):
        return "code"
    if any(w in p for w in ["analyze", "review", "explain", "why", "how does"]):
        return "reasoning"
    return "security_research"


def handle(prompt, user_id, session_id=None, prefer=None, target=None):
    # Scope check
    if target:
        ok, reason = enforce_scope(target, session_id)
        if not ok:
            audit_repo.log("scope.blocked",
                           {"target": target, "reason": reason}, user_id=user_id)
            return {"ok": False, "error": f"Target out of scope: {reason}",
                    "scope_blocked": True}

    # Session bootstrap
    if not session_id:
        session_id = chat_repo.new_session(user_id, title=prompt[:60])

    # History + system
    history = chat_repo.history(session_id, user_id, limit=20)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [
        {"role": "user", "content": prompt}
    ]

    task_type = classify(prompt)
    log.info(f"session={str(session_id)[:8]} task={task_type} u={str(user_id)[:8]}")

    # Save user msg
    chat_repo.add(session_id, user_id, "user", prompt)

    try:
        result = router.chat(messages, task_type=task_type, prefer=prefer)
    except Exception as e:
        audit_repo.log("llm.failed", {"error": str(e)}, user_id=user_id)
        return {"ok": False, "error": str(e), "session_id": session_id}

    chat_repo.add(session_id, user_id, "assistant", result["content"],
                  provider=result["provider"], model=result["model"],
                  elapsed_ms=result.get("elapsed_ms"))
    audit_repo.log("llm.success", {
        "provider": result["provider"], "model": result["model"],
        "task_type": task_type, "elapsed_ms": result["elapsed_ms"],
    }, user_id=user_id)

    return {"ok": True, "session_id": session_id, "task_type": task_type, **result}
