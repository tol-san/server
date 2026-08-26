"""
Redis ZSET/TTL presence manager.

Each active connection stores:
  presence:connection:{connection_id}  → "{user_id}:{community_id}"   TTL=90s

Active connections per community tracked in a sorted set:
  presence:chat:{community_id}  ZSET  score=last_seen_timestamp  member=connection_id

A heartbeat refreshes both TTL and the ZSET score.
Stale entries (score < now-90s) are pruned on read.
"""
import time
import uuid
import logging
from typing import List, Set
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

_PRESENCE_TTL = 90          # seconds
_STALE_THRESHOLD = 90       # seconds — same as TTL


class PresenceManager:
    """Redis-backed online presence tracker using ZSET + per-connection TTL keys."""

    def _conn_key(self, connection_id: str) -> str:
        return f"presence:connection:{connection_id}"

    def _chat_key(self, community_id: str) -> str:
        return f"presence:chat:{community_id}"

    async def join(
        self,
        community_id: str,
        connection_id: str,
        user_id: str,
    ) -> None:
        try:
            r = get_redis_client()
            now = time.time()
            pipe = r.pipeline()
            pipe.set(
                self._conn_key(connection_id),
                f"{user_id}:{community_id}",
                ex=_PRESENCE_TTL,
            )
            pipe.zadd(self._chat_key(community_id), {connection_id: now})
            await pipe.execute()
        except Exception as exc:
            logger.debug("presence.join failed: %s", exc)

    async def leave(self, community_id: str, connection_id: str) -> None:
        try:
            r = get_redis_client()
            pipe = r.pipeline()
            pipe.delete(self._conn_key(connection_id))
            pipe.zrem(self._chat_key(community_id), connection_id)
            await pipe.execute()
        except Exception as exc:
            logger.debug("presence.leave failed: %s", exc)

    async def heartbeat(self, community_id: str, connection_id: str) -> None:
        try:
            r = get_redis_client()
            now = time.time()
            pipe = r.pipeline()
            pipe.expire(self._conn_key(connection_id), _PRESENCE_TTL)
            pipe.zadd(self._chat_key(community_id), {connection_id: now})
            await pipe.execute()
        except Exception as exc:
            logger.debug("presence.heartbeat failed: %s", exc)

    async def get_online_connection_ids(self, community_id: str) -> List[str]:
        """Return connection IDs seen within the last STALE_THRESHOLD seconds."""
        try:
            r = get_redis_client()
            min_score = time.time() - _STALE_THRESHOLD
            # Prune stale entries first
            await r.zremrangebyscore(self._chat_key(community_id), "-inf", min_score)
            return await r.zrangebyscore(
                self._chat_key(community_id), min_score, "+inf"
            )
        except Exception as exc:
            logger.debug("presence.get_online failed: %s", exc)
            return []

    async def get_online_user_ids(self, community_id: str) -> Set[str]:
        """Return unique user IDs currently online in a community."""
        connection_ids = await self.get_online_connection_ids(community_id)
        if not connection_ids:
            return set()
        try:
            r = get_redis_client()
            keys = [self._conn_key(cid) for cid in connection_ids]
            values = await r.mget(*keys)
            user_ids: Set[str] = set()
            for val in values:
                if val:
                    user_id = val.split(":")[0]
                    user_ids.add(user_id)
            return user_ids
        except Exception as exc:
            logger.debug("presence.get_user_ids failed: %s", exc)
            return set()

    async def count_online(self, community_id: str) -> int:
        user_ids = await self.get_online_user_ids(community_id)
        return len(user_ids)


presence_manager = PresenceManager()
