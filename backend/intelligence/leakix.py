"""LeakIX — leak / exposure search engine."""
import requests
from backend.config import Config


def _headers():
    k = Config.INTEL_KEYS.get("leakix")
    if not k:
        return {"Accept": "application/json"}
    return {"api-key": k, "Accept": "application/json"}


def host_lookup(host: str) -> dict:
    r = requests.get(f"https://leakix.net/host/{host}",
                     headers=_headers(), timeout=30)
    return r.json() if r.status_code < 400 else {"error": r.text[:200]}


def search(query: str, scope: str = "leak", page: int = 0) -> dict:
    """scope: leak | service"""
    r = requests.get("https://leakix.net/search",
                     headers=_headers(),
                     params={"q": query, "scope": scope, "page": page},
                     timeout=30)
    return r.json() if r.status_code < 400 else {"error": r.text[:200]}
