import logging

from commerce.cache import cache
from commerce.members import MEMBERS

logger = logging.getLogger(__name__)

SUBSCRIPTIONS = {
    "H-1": [7, 15],
    "W-1": [11, 7],
    "D-1": [11],
}

_PREFERENCES = {
    7: {"channel": "email", "restock": True},
    11: {"channel": "push", "restock": True},
    15: {"channel": "email", "restock": False},
}


def load_preferences() -> dict:
    cached = cache.get("notification_preferences")
    if cached is not None:
        return cached
    prefs = {member_id: dict(p) for member_id, p in _PREFERENCES.items()}
    cache.set("notification_preferences", prefs, ttl=300)
    return prefs


def notify_restock(sku: str) -> list[str]:
    prefs = load_preferences()
    sent: list[str] = []
    for member_id in SUBSCRIPTIONS.get(sku, []):
        pref = prefs[member_id]
        if not pref["restock"]:
            continue
        member = MEMBERS[member_id]
        sent.append(f"{pref['channel']}:{member['email']}:{sku}")
    logger.info("restock %s notified %s", sku, sent)
    return sent
