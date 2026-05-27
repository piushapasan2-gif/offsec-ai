"""VirusTotal API v3 wrapper — file/url/ip/domain reputation."""
import requests
from backend.config import Config
from backend.core import cache
from backend.utils.quota_manager import consume, check

BASE = "https://www.virustotal.com/api/v3"


def _headers():
    k = Config.INTEL_KEYS.get("virustotal")
    if not k:
        raise RuntimeError("VirusTotal API key not configured")
    return {"x-apikey": k}


def _get(path: str, cache_ns: str, *cache_parts, ttl: int = 86400) -> dict:
    cached = cache.get(cache_ns, *cache_parts)
    if cached:
        return {**cached, "_cached": True}
    if not check("virustotal")[0]:
        return {"error": "VT quota exhausted"}
    r = requests.get(f"{BASE}{path}", headers=_headers(), timeout=30)
    consume("virustotal")
    if r.status_code == 404:
        return {"found": False}
    if r.status_code >= 400:
        return {"error": f"{r.status_code} {r.text[:200]}"}
    data = r.json()
    cache.set_(cache_ns, data, *cache_parts, ttl=ttl)
    return data


def ip_info(ip: str):
    return _get(f"/ip_addresses/{ip}", "vt.ip", ip)


def domain_info(domain: str):
    return _get(f"/domains/{domain}", "vt.domain", domain)


def file_hash_info(hash_: str):
    return _get(f"/files/{hash_}", "vt.hash", hash_)


def url_scan(url: str) -> dict:
    """Submit URL for scanning."""
    if not check("virustotal")[0]:
        return {"error": "VT quota exhausted"}
    r = requests.post(f"{BASE}/urls", headers=_headers(),
                      data={"url": url}, timeout=30)
    consume("virustotal")
    return r.json() if r.status_code < 400 else {"error": r.text[:200]}
