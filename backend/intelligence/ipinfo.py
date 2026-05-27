"""IPInfo wrapper — IP geolocation + ASN."""
import requests
from backend.config import Config
from backend.core import cache


def lookup(ip: str) -> dict:
    k = Config.INTEL_KEYS.get("ipinfo")
    if not k:
        return {"error": "IPInfo key missing"}
    cached = cache.get("ipinfo.lookup", ip)
    if cached:
        return {**cached, "_cached": True}
    r = requests.get(f"https://ipinfo.io/{ip}?token={k}", timeout=15)
    if r.status_code >= 400:
        return {"error": f"{r.status_code} {r.text[:200]}"}
    data = r.json()
    cache.set_("ipinfo.lookup", data, ip, ttl=86400 * 7)
    return data


def my_ip() -> dict:
    k = Config.INTEL_KEYS.get("ipinfo")
    r = requests.get(f"https://ipinfo.io?token={k}" if k else "https://ipinfo.io",
                     timeout=10)
    return r.json() if r.status_code < 400 else {}
