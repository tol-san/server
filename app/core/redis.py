import logging
from typing import Optional
import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client instance
redis_client: Optional[aioredis.Redis] = None

# Fallback in-memory storage for test/offline environments
_in_memory_blacklist: dict[str, float] = {}


def get_redis_client() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2.0,
        )
    return redis_client


async def blacklist_token(jti: str, expire_seconds: int) -> None:
    """Store a revoked JWT ID (jti) in Redis with TTL equal to the token lifetime."""
    if expire_seconds <= 0:
        return
    try:
        client = get_redis_client()
        await client.set(f"blacklist:{jti}", "revoked", ex=expire_seconds)
    except Exception as exc:
        logger.warning("Redis blacklist failed, falling back to memory: %s", exc)
        import time
        _in_memory_blacklist[jti] = time.time() + expire_seconds


async def is_token_blacklisted(jti: str) -> bool:
    """Check if a JWT ID (jti) has been revoked."""
    import time
    if jti in _in_memory_blacklist:
        if time.time() < _in_memory_blacklist[jti]:
            return True
        else:
            del _in_memory_blacklist[jti]

    try:
        client = get_redis_client()
        result = await client.get(f"blacklist:{jti}")
        return result is not None
    except Exception as exc:
        logger.warning("Redis check failed: %s", exc)
        return False


async def close_redis() -> None:
    """Gracefully close Redis connections."""
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None
