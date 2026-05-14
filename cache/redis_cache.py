import time
from typing import Any


class RedisReadyCache:
    def __init__(self) -> None:
        self._memory: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._memory.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at and expires_at < time.time():
            self._memory.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        self._memory[key] = (time.time() + ttl_seconds if ttl_seconds else 0, value)
