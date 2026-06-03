"""
Smart router — picks the right LLM for the task, falls back on failure.
Supports both blocking .chat() and streaming .stream() modes.
"""
from __future__ import annotations
import time
from typing import List, Dict, Optional, Generator
from backend.core.ai_engine import PROVIDERS, ProviderError
from backend.utils.logger import get_logger

log = get_logger("router")

PREFERENCES = {
    "reasoning":         ["anthropic", "openai", "deepseek", "groq", "google"],
    "code":              ["anthropic", "deepseek", "openai", "groq"],
    "fast":              ["groq", "deepseek", "google", "together"],
    "web_grounded":      ["perplexity", "openrouter", "google"],
    "creative":          ["anthropic", "openai", "xai", "mistral"],
    "security_research": ["anthropic", "deepseek", "openai", "xai", "openrouter"],
    "long_context":      ["google", "anthropic", "openai"],
    "exploit_dev":       ["deepseek", "anthropic", "openai", "groq"],
    "ctf_solve":         ["anthropic", "deepseek", "openai", "groq"],
    "default":           ["anthropic", "openai", "google", "groq", "deepseek",
                          "mistral", "openrouter", "together", "xai", "cohere", "huggingface"],
}


def pick_provider(task_type: str = "default", prefer: Optional[str] = None):
    if prefer and prefer in PROVIDERS:
        order = [prefer] + [p for p in PREFERENCES.get(task_type, PREFERENCES["default"]) if p != prefer]
    else:
        order = PREFERENCES.get(task_type, PREFERENCES["default"])
    return [PROVIDERS[p] for p in order if p in PROVIDERS]


def chat(messages: List[Dict], task_type: str = "default",
         prefer: Optional[str] = None, model: Optional[str] = None,
         temperature: float = 0.7, max_tokens: int = 2048) -> Dict:
    candidates = pick_provider(task_type, prefer)
    if not candidates:
        raise RuntimeError("No LLM providers configured. Check your .env")
    attempts = []
    t0 = time.time()
    for p in candidates:
        try:
            log.info(f"[router] task={task_type} -> {p.name}")
            content = p.chat(messages, model=model, temperature=temperature, max_tokens=max_tokens)
            return {
                "provider": p.name,
                "model": model or p.default_model,
                "content": content,
                "attempts": attempts + [{"provider": p.name, "status": "ok"}],
                "elapsed_ms": int((time.time() - t0) * 1000),
            }
        except ProviderError as e:
            log.warning(f"[router] {p.name} failed: {e}")
            attempts.append({"provider": p.name, "status": "failed", "error": str(e)})
        except Exception as e:
            log.error(f"[router] {p.name} unexpected: {e}")
            attempts.append({"provider": p.name, "status": "error", "error": str(e)})
    raise RuntimeError(f"All providers failed for task={task_type}: {attempts}")


def stream(messages: List[Dict], task_type: str = "default",
           prefer: Optional[str] = None, model: Optional[str] = None,
           temperature: float = 0.7, max_tokens: int = 2048) -> Generator[Dict, None, None]:
    """
    Try providers in order. Yields dicts:
      {"type": "meta",  "provider": ..., "model": ...}
      {"type": "token", "text": "..."}
      {"type": "done",  "elapsed_ms": ...}
    Falls back to next provider if one fails.
    """
    candidates = pick_provider(task_type, prefer)
    if not candidates:
        raise RuntimeError("No LLM providers configured. Check your .env")
    t0 = time.time()
    for p in candidates:
        try:
            log.info(f"[router.stream] task={task_type} -> {p.name}")
            yield {"type": "meta", "provider": p.name, "model": model or p.default_model}
            for token in p.stream(messages, model=model, temperature=temperature, max_tokens=max_tokens):
                yield {"type": "token", "text": token}
            yield {"type": "done", "elapsed_ms": int((time.time() - t0) * 1000)}
            return
        except Exception as e:
            log.warning(f"[router.stream] {p.name} failed: {e}")
            continue
    raise RuntimeError(f"All providers failed streaming task={task_type}")


def health_check() -> Dict[str, str]:
    results = {}
    for name, p in PROVIDERS.items():
        try:
            r = p.chat([{"role": "user", "content": "ping"}], max_tokens=10)
            results[name] = "OK" if r else "EMPTY"
        except Exception as e:
            results[name] = f"FAIL: {str(e)[:80]}"
    return results
