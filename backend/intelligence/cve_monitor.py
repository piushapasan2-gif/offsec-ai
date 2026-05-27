"""NVD CVE lookups + monitoring."""
import requests
from backend.config import Config
from backend.core import cache

BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def _params(extra: dict = None) -> dict:
    p = dict(extra or {})
    k = Config.INTEL_KEYS.get("nvd")
    if k:
        p["apiKey"] = k
    return p


def cve_lookup(cve_id: str) -> dict:
    cached = cache.get("nvd.cve", cve_id)
    if cached:
        return {**cached, "_cached": True}
    r = requests.get(BASE, params=_params({"cveId": cve_id}), timeout=30)
    if r.status_code >= 400:
        return {"error": f"{r.status_code} {r.text[:200]}"}
    data = r.json()
    cache.set_("nvd.cve", data, cve_id, ttl=86400 * 7)
    return data


def search(keyword: str, limit: int = 20) -> dict:
    r = requests.get(BASE, params=_params({
        "keywordSearch": keyword, "resultsPerPage": limit
    }), timeout=30)
    return r.json() if r.status_code < 400 else {"error": r.text[:200]}


def critical_recent(days: int = 7) -> dict:
    """Recent CVEs with CVSS >= 9.0."""
    from datetime import datetime, timedelta
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    r = requests.get(BASE, params=_params({
        "pubStartDate": start.strftime("%Y-%m-%dT00:00:00.000"),
        "pubEndDate":   end.strftime("%Y-%m-%dT23:59:59.999"),
        "cvssV3Severity": "CRITICAL",
        "resultsPerPage": 100,
    }), timeout=30)
    return r.json() if r.status_code < 400 else {"error": r.text[:200]}
