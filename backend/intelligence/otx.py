"""AlienVault OTX (Open Threat Exchange) wrapper."""
import requests
from backend.config import Config
from backend.core import cache

BASE = "https://otx.alienvault.com/api/v1"


def _headers():
    k = Config.INTEL_KEYS.get("otx")
    if not k:
        raise RuntimeError("OTX API key not configured")
    return {"X-OTX-API-KEY": k}


def _get(path: str, cache_ns: str, *parts, ttl: int = 3600):
    cached = cache.get(cache_ns, *parts)
    if cached:
        return {**cached, "_cached": True}
    r = requests.get(f"{BASE}{path}", headers=_headers(), timeout=30)
    if r.status_code >= 400:
        return {"error": f"{r.status_code} {r.text[:200]}"}
    data = r.json()
    cache.set_(cache_ns, data, *parts, ttl=ttl)
    return data


def ip_indicators(ip: str, section: str = "general"):
    return _get(f"/indicators/IPv4/{ip}/{section}", "otx.ip", ip, section)


def domain_indicators(domain: str, section: str = "general"):
    return _get(f"/indicators/domain/{domain}/{section}", "otx.domain", domain, section)


def file_hash_indicators(hash_: str, section: str = "general"):
    return _get(f"/indicators/file/{hash_}/{section}", "otx.hash", hash_, section)


def pulses(query: str = "", limit: int = 20):
    return _get(f"/search/pulses?q={query}&limit={limit}", "otx.pulses", query, limit)
