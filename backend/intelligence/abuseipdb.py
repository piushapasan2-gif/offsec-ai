"""AbuseIPDB — IP reputation checker."""
import requests
from backend.config import Config
from backend.core import cache
from backend.utils.quota_manager import consume, check


def _headers():
    k = Config.INTEL_KEYS.get("abuseipdb")
    if not k:
        raise RuntimeError("AbuseIPDB API key not configured")
    return {"Key": k, "Accept": "application/json"}


def check_ip(ip: str, max_age_days: int = 90):
    cached = cache.get("abuseipdb.check", ip)
    if cached:
        return {**cached, "_cached": True}
    if not check("abuseipdb")[0]:
        return {"error": "AbuseIPDB quota exhausted"}
    r = requests.get("https://api.abuseipdb.com/api/v2/check",
                     headers=_headers(),
                     params={"ipAddress": ip, "maxAgeInDays": max_age_days,
                             "verbose": "true"},
                     timeout=30)
    consume("abuseipdb")
    if r.status_code >= 400:
        return {"error": f"{r.status_code} {r.text[:200]}"}
    data = r.json().get("data", {})
    cache.set_("abuseipdb.check", data, ip, ttl=86400)
    return data
