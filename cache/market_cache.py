from typing import Any

from cache.redis_cache import RedisReadyCache


market_cache = RedisReadyCache()
news_cache = RedisReadyCache()
semantic_cache = RedisReadyCache()


def cache_market_data(key: str, value: Any, ttl_seconds: int = 120) -> None:
    market_cache.set(key, value, ttl_seconds)
