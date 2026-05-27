"""urlscan.io wrapper — URL screenshot + behavior analysis."""
import requests
from backend.config import Config


def _headers():
    k = Config.INTEL_KEYS.get("urlscan")
    if not k:
        raise RuntimeError("URLScan API key not configured")
    return {"API-Key": k, "Content-Type": "application/json"}


def submit(url: str, visibility: str = "public") -> dict:
    """Submit URL for scanning. Visibility: public|unlisted|private."""
    r = requests.post("https://urlscan.io/api/v1/scan/",
                      headers=_headers(),
                      json={"url": url, "visibility": visibility},
                      timeout=30)
    return r.json() if r.status_code < 400 else {"error": r.text[:200]}


def result(uuid: str) -> dict:
    r = requests.get(f"https://urlscan.io/api/v1/result/{uuid}/", timeout=30)
    return r.json() if r.status_code < 400 else {"error": r.text[:200]}


def search(query: str, size: int = 10) -> dict:
    r = requests.get("https://urlscan.io/api/v1/search/",
                     headers=_headers(),
                     params={"q": query, "size": size},
                     timeout=30)
    return r.json() if r.status_code < 400 else {"error": r.text[:200]}
