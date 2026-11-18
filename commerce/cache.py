import json
import time
from typing import Any


class TTLCache:
    def __init__(self) -> None:
        self._items: dict[str, tuple[float, str]] = {}

    def set(self, key: str, value: Any, ttl: float) -> None:
        self._items[key] = (time.monotonic() + ttl, json.dumps(value))

    def get(self, key: str) -> Any | None:
        item = self._items.get(key)
        if item is None:
            return None
        expires_at, payload = item
        if time.monotonic() > expires_at:
            del self._items[key]
            return None
        return json.loads(payload)


cache = TTLCache()
