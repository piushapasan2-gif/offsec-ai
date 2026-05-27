"""GitHub API — repo dorking, code search, secret scanning."""
import requests
from backend.config import Config


def _headers():
    h = {"Accept": "application/vnd.github+json"}
    if Config.GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {Config.GITHUB_TOKEN}"
    return h


def code_search(query: str, per_page: int = 30) -> dict:
    """Search code. Example: 'AKIA in:file extension:env'"""
    r = requests.get("https://api.github.com/search/code",
                     headers=_headers(),
                     params={"q": query, "per_page": per_page},
                     timeout=30)
    return r.json() if r.status_code < 400 else {"error": r.text[:200]}


def repo_search(query: str) -> dict:
    r = requests.get("https://api.github.com/search/repositories",
                     headers=_headers(),
                     params={"q": query, "sort": "stars"},
                     timeout=30)
    return r.json() if r.status_code < 400 else {"error": r.text[:200]}


def commits_search(query: str) -> dict:
    """Search commits — useful for finding leaked creds in history."""
    r = requests.get("https://api.github.com/search/commits",
                     headers={**_headers(), "Accept": "application/vnd.github.cloak-preview"},
                     params={"q": query},
                     timeout=30)
    return r.json() if r.status_code < 400 else {"error": r.text[:200]}


def org_recon(org: str) -> dict:
    """Get repos + members for an organization."""
    repos = requests.get(f"https://api.github.com/orgs/{org}/repos",
                         headers=_headers(),
                         params={"per_page": 100},
                         timeout=30).json()
    members = requests.get(f"https://api.github.com/orgs/{org}/members",
                           headers=_headers(),
                           timeout=30).json()
    return {"repos": repos, "members": members}
