"""
Smart router — picks the right LLM for the task, falls back on failure.

Task-to-provider preferences:
  - reasoning/code     → anthropic > openai > deepseek > groq
  - fast/cheap         → groq > deepseek > gemini > together
  - web-grounded       → perplexity > openrouter
  - creative/brainstorm→ anthropic > openai > xai
  - security_research  → anthropic > openai > deepseek (uncensored-ish)
  - long_context       → google (gemini 2M) > anthropic
  - default            → first available in preference order
"""
from __future__ import annotations
import time
from typing import List, Dict, Optional
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
    """Return list of providers (in preferred order) that have keys configured."""
    if prefer and prefer in PROVIDERS:
        order = [prefer] + [p for p in PREFERENCES.get(task_type, PREFERENCES["default"]) if p != prefer]
    else:
        order = PREFERENCES.get(task_type, PREFERENCES["default"])
    return [PROVIDERS[p] for p in order if p in PROVIDERS]


def chat(messages: List[Dict], task_type: str = "default",
         prefer: Optional[str] = None, model: Optional[str] = None,
         temperature: float = 0.7, max_tokens: int = 2048) -> Dict:
    """
    Try providers in preference order until one succeeds.
    Returns {provider, model, content, attempts, elapsed_ms}.
    """
    candidates = pick_provider(task_type, prefer)
    if not candidates:
        raise RuntimeError("No LLM providers configured. Check your .env")

    attempts = []
    t0 = time.time()
    for p in candidates:
        try:
            log.info(f"[router] task={task_type} → trying {p.name}")
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
            continue
        except Exception as e:
            log.error(f"[router] {p.name} unexpected: {e}")
            attempts.append({"provider": p.name, "status": "error", "error": str(e)})
            continue

    raise RuntimeError(f"All providers failed for task={task_type}: {attempts}")


def health_check() -> Dict[str, str]:
    """Ping each provider with a tiny prompt to verify keys work."""
    results = {}
    for name, p in PROVIDERS.items():
        try:
            r = p.chat([{"role": "user", "content": "ping"}], max_tokens=10)
            results[name] = "OK" if r else "EMPTY"
        except Exception as e:
            results[name] = f"FAIL: {str(e)[:80]}"
    return results
