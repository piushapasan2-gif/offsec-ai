"""Discord webhook notifier."""
import requests
from backend.config import Config


def notify(message: str, username: str = "OffSec AI", embeds: list = None) -> bool:
    url = Config.DISCORD_WEBHOOK
    if not url:
        return False
    payload = {"content": message, "username": username}
    if embeds:
        payload["embeds"] = embeds
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code in (200, 204)
    except Exception:
        return False


def alert(title: str, description: str, severity: str = "info") -> bool:
    colors = {"critical": 15158332, "high": 16089871, "medium": 16763904,
              "low": 3447003, "info": 3066993}
    embed = {
        "title": title,
        "description": description,
        "color": colors.get(severity.lower(), 3066993),
    }
    return notify("", embeds=[embed])
