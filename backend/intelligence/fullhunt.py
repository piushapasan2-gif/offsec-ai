"""FullHunt — attack surface monitoring."""
import requests
from backend.config import Config


def _headers():
    k = Config.INTEL_KEYS.get("fullhunt")
    if not k:
        raise RuntimeError("FullHunt API key not configured")
    return {"X-API-KEY": k}


def domain_details(domain: str) -> dict:
    r = requests.get(f"https://fullhunt.io/api/v1/domain/{domain}/details",
                     headers=_headers(), timeout=30)
    return r.json() if r.status_code < 400 else {"error": r.text[:200]}


def subdomains(domain: str) -> dict:
    r = requests.get(f"https://fullhunt.io/api/v1/domain/{domain}/subdomains",
                     headers=_headers(), timeout=30)
    return r.json() if r.status_code < 400 else {"error": r.text[:200]}
