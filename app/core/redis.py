import logging
from typing import Optional
import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client instance
redis_client: Optional[aioredis.Redis] = None

# Fallback in-memory storage for test/offline environments
_in_memory_blacklist: dict[str, float] = {}
_MAX_BLACKLIST_SIZE = 10000  # Maximum revoked tokens in memory fallback


def get_redis_client() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=5.0,
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
        now = time.time()
        expired = [k for k, exp in _in_memory_blacklist.items() if now >= exp]
        for k in expired:
            del _in_memory_blacklist[k]
        if len(_in_memory_blacklist) >= _MAX_BLACKLIST_SIZE:
            items = sorted(_in_memory_blacklist.items(), key=lambda x: x[1])
            for k, _ in items[:_MAX_BLACKLIST_SIZE // 2]:
                del _in_memory_blacklist[k]
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


async def add_to_stream(stream_name: str, fields: dict) -> Optional[str]:
    """Append an event to a Redis Stream (durable event log)."""
    try:
        client = get_redis_client()
        # Convert all values in fields to string
        str_fields = {k: str(v) if v is not None else "" for k, v in fields.items()}
        msg_id = await client.xadd(stream_name, str_fields)
        return msg_id
    except Exception as exc:
        logger.debug("Redis stream add failed (%s): %s", stream_name, exc)
        return None


async def read_from_stream(
    stream_name: str,
    last_id: str = "$",
    count: int = 10,
    block_ms: int = 2000,
) -> list:
    """Read new events from a Redis Stream."""
    try:
        client = get_redis_client()
        res = await client.xread({stream_name: last_id}, count=count, block=block_ms)
        return res or []
    except Exception as exc:
        logger.debug("Redis stream read failed (%s): %s", stream_name, exc)
        return []


async def publish_pubsub(channel: str, message: str) -> int:
    """Publish ephemeral message via Redis Pub/Sub (fire-and-forget, e.g. typing indicators)."""
    try:
        client = get_redis_client()
        return await client.publish(channel, message)
    except Exception as exc:
        logger.debug("Redis pub/sub failed on channel %s: %s", channel, exc)
        return 0


async def close_redis() -> None:
    """Gracefully close Redis connections."""
    global redis_client
    if redis_client is not None:
        try:
            await redis_client.aclose()
        except Exception as exc:
            logger.warning("Error closing Redis client: %s", exc)
        finally:
            redis_client = None
