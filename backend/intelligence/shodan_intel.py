"""Shodan API wrapper — host info, search, exploit DB."""
import requests
from backend.config import Config
from backend.core import cache
from backend.utils.quota_manager import consume, check

BASE = "https://api.shodan.io"


def _key():
    k = Config.INTEL_KEYS.get("shodan")
    if not k:
        raise RuntimeError("Shodan API key not configured")
    return k


def host_info(ip: str, history: bool = False) -> dict:
    cached = cache.get("shodan.host", ip, history)
    if cached:
        return {**cached, "_cached": True}
    if not check("shodan")[0]:
        return {"error": "Shodan quota exhausted"}
    r = requests.get(f"{BASE}/shodan/host/{ip}",
                     params={"key": _key(), "history": str(history).lower()},
                     timeout=30)
    consume("shodan")
    if r.status_code == 404:
        return {"ip": ip, "found": False}
    if r.status_code >= 400:
        return {"error": f"{r.status_code} {r.text[:200]}"}
    data = r.json()
    cache.set_("shodan.host", data, ip, history, ttl=86400)
    return data


def search(query: str, page: int = 1) -> dict:
    cached = cache.get("shodan.search", query, page)
    if cached:
        return {**cached, "_cached": True}
    if not check("shodan")[0]:
        return {"error": "Shodan quota exhausted"}
    r = requests.get(f"{BASE}/shodan/host/search",
                     params={"key": _key(), "query": query, "page": page},
                     timeout=30)
    consume("shodan")
    if r.status_code >= 400:
        return {"error": f"{r.status_code} {r.text[:200]}"}
    data = r.json()
    cache.set_("shodan.search", data, query, page, ttl=3600)
    return data


def my_ip() -> str:
    r = requests.get(f"{BASE}/tools/myip", params={"key": _key()}, timeout=10)
    return r.text.strip().strip('"')


def api_info() -> dict:
    r = requests.get(f"{BASE}/api-info", params={"key": _key()}, timeout=10)
    return r.json() if r.status_code == 200 else {"error": r.text[:200]}
