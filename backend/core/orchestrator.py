"""Orchestrator — handles user requests, both blocking and streaming."""
import json
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


def _setup(prompt, user_id, session_id=None, target=None):
    """Common setup for handle() and handle_stream(): scope check + session + history."""
    if target:
        ok, reason = enforce_scope(target, session_id)
        if not ok:
            audit_repo.log("scope.blocked", {"target": target, "reason": reason}, user_id=user_id)
            return None, None, None, {"ok": False, "error": f"Target out of scope: {reason}", "scope_blocked": True}

    if not session_id:
        session_id = chat_repo.new_session(user_id, title=prompt[:60])

    history = chat_repo.history(session_id, user_id, limit=20)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [
        {"role": "user", "content": prompt}
    ]
    task_type = classify(prompt)
    chat_repo.add(session_id, user_id, "user", prompt)
    return session_id, messages, task_type, None


def handle(prompt, user_id, session_id=None, prefer=None, target=None):
    """Blocking handler — returns full response dict."""
    session_id, messages, task_type, err = _setup(prompt, user_id, session_id, target)
    if err:
        return err

    log.info(f"session={str(session_id)[:8]} task={task_type}")
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


def handle_stream(prompt, user_id, session_id=None, prefer=None, target=None):
    """
    Streaming handler — yields SSE-ready dicts.
    Caller serialises to: data: <json>\n\n
    """
    session_id, messages, task_type, err = _setup(prompt, user_id, session_id, target)
    if err:
        yield err
        return

    log.info(f"[stream] session={str(session_id)[:8]} task={task_type}")

    full_content = []
    provider_name = ""
    model_name = ""

    try:
        for chunk in router.stream(messages, task_type=task_type, prefer=prefer):
            if chunk["type"] == "meta":
                provider_name = chunk["provider"]
                model_name = chunk["model"]
                yield {"type": "meta", "provider": provider_name, "model": model_name,
                       "session_id": session_id, "task_type": task_type}
            elif chunk["type"] == "token":
                full_content.append(chunk["text"])
                yield {"type": "token", "text": chunk["text"]}
            elif chunk["type"] == "done":
                assembled = "".join(full_content)
                chat_repo.add(session_id, user_id, "assistant", assembled,
                              provider=provider_name, model=model_name,
                              elapsed_ms=chunk.get("elapsed_ms"))
                audit_repo.log("llm.success", {
                    "provider": provider_name, "model": model_name,
                    "task_type": task_type, "elapsed_ms": chunk.get("elapsed_ms"),
                }, user_id=user_id)
                yield {"type": "done", "session_id": session_id,
                       "elapsed_ms": chunk.get("elapsed_ms")}
    except Exception as e:
        audit_repo.log("llm.failed", {"error": str(e)}, user_id=user_id)
        yield {"type": "error", "error": str(e), "session_id": session_id}
