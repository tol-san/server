import json
import logging
import time
from typing import Any, Dict, Optional
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

_MAX_MEMORY_CACHE_SIZE = 1000  # Maximum entries in fallback in-memory cache

# Fallback in-memory cache for offline/testing setups
_in_memory_cache: Dict[str, tuple[Any, float]] = {}


class CacheService:
    """Centralized asynchronous caching service backed by Redis with in-memory fallback."""

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value by key, returning None on cache miss or expiration."""
        # 1. Try Redis
        try:
            client = get_redis_client()
            val = await client.get(key)
            if val is not None:
                return json.loads(val)
        except Exception as exc:
            logger.debug("Redis cache GET miss/fallback for %s: %s", key, exc)

        # 2. Check in-memory fallback
        if key in _in_memory_cache:
            val, expiry = _in_memory_cache[key]
            if time.time() < expiry:
                return val
            else:
                del _in_memory_cache[key]

        return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Store a JSON-serializable value in cache with a Time-To-Live in seconds."""
        if ttl <= 0:
            return False

        serialized = json.dumps(value)

        # 1. Try Redis
        try:
            client = get_redis_client()
            await client.set(key, serialized, ex=ttl)
            return True
        except Exception as exc:
            logger.debug("Redis cache SET fallback for %s: %s", key, exc)

        # 2. Store in memory fallback
        if len(_in_memory_cache) >= _MAX_MEMORY_CACHE_SIZE:
            now = time.time()
            expired_keys = [k for k, (_, exp) in _in_memory_cache.items() if now >= exp]
            for k in expired_keys:
                del _in_memory_cache[k]
            if len(_in_memory_cache) >= _MAX_MEMORY_CACHE_SIZE:
                oldest_keys = list(_in_memory_cache.keys())[:_MAX_MEMORY_CACHE_SIZE // 2]
                for k in oldest_keys:
                    del _in_memory_cache[k]
        _in_memory_cache[key] = (value, time.time() + ttl)
        return True

    async def delete(self, key: str) -> bool:
        """Delete a single key from cache."""
        deleted = False
        try:
            client = get_redis_client()
            await client.delete(key)
            deleted = True
        except Exception as exc:
            logger.debug("Redis cache DELETE failed for %s: %s", key, exc)

        if key in _in_memory_cache:
            del _in_memory_cache[key]
            deleted = True

        return deleted

    async def delete_pattern(self, pattern: str) -> int:
        """Scan and delete all keys matching a glob-style pattern (e.g. 'cache:feed:home:123:*')."""
        deleted_count = 0
        try:
            client = get_redis_client()
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    await client.delete(*keys)
                    deleted_count += len(keys)
                if cursor == 0:
                    break
        except Exception as exc:
            logger.debug("Redis cache DELETE PATTERN failed for %s: %s", pattern, exc)

        # In-memory pattern cleanup
        import fnmatch

        to_remove = [k for k in _in_memory_cache if fnmatch.fnmatch(k, pattern)]
        for k in to_remove:
            del _in_memory_cache[k]
            deleted_count += 1

        return deleted_count

    async def incr(self, key: str, amount: int = 1) -> int:
        """Atomically increment a numerical counter in cache."""
        try:
            client = get_redis_client()
            return await client.incrby(key, amount)
        except Exception as exc:
            logger.debug("Redis cache INCR fallback for %s: %s", key, exc)

        # In-memory counter
        cur, exp = _in_memory_cache.get(key, (0, time.time() + 86400))
        new_val = int(cur) + amount
        _in_memory_cache[key] = (new_val, exp)
        return new_val


cache_service = CacheService()
