"""Thin Supabase REST client - no extra deps, uses requests."""
import requests
from backend.config import Config


class SupabaseClient:
    def __init__(self, service: bool = True):
        self.url = Config.SUPABASE_URL
        self.key = Config.SUPABASE_SERVICE_KEY if service else Config.SUPABASE_ANON_KEY
        if not self.url or not self.key:
            raise RuntimeError("Supabase not configured (SUPABASE_URL/KEY missing in .env)")
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _req(self, method, path, **kwargs):
        url = f"{self.url}{path}"
        r = requests.request(method, url, headers=self.headers, timeout=30, **kwargs)
        if r.status_code >= 400:
            raise RuntimeError(f"Supabase {r.status_code}: {r.text[:200]}")
        return r.json() if r.text else None

    def insert(self, table, row):
        return self._req("POST", f"/rest/v1/{table}", json=row)

    def insert_many(self, table, rows):
        return self._req("POST", f"/rest/v1/{table}", json=rows)

    def select(self, table, filters=None, order=None, limit=None):
        params = filters or {}
        if order:
            params["order"] = order
        if limit:
            params["limit"] = str(limit)
        return self._req("GET", f"/rest/v1/{table}", params=params)

    def update(self, table, filters, patch):
        return self._req("PATCH", f"/rest/v1/{table}", params=filters, json=patch)

    def delete(self, table, filters):
        return self._req("DELETE", f"/rest/v1/{table}", params=filters)

    def rpc(self, fn_name, args=None):
        return self._req("POST", f"/rest/v1/rpc/{fn_name}", json=args or {})

    def verify_jwt(self, jwt: str) -> dict:
        """Call Supabase Auth to verify a user JWT. Returns user info or raises."""
        r = requests.get(
            f"{self.url}/auth/v1/user",
            headers={"apikey": Config.SUPABASE_ANON_KEY, "Authorization": f"Bearer {jwt}"},
            timeout=15,
        )
        if r.status_code != 200:
            raise RuntimeError(f"JWT invalid: {r.status_code}")
        return r.json()


_client = None


def get_client() -> SupabaseClient:
    global _client
    if _client is None:
        _client = SupabaseClient(service=True)
    return _client


def is_configured() -> bool:
    return bool(Config.SUPABASE_URL and Config.SUPABASE_SERVICE_KEY)
