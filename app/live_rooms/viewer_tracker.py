"""
Redis-backed live viewer tracking.

Key design (per research report):
  SET/ZSET  → current active participants (can be removed on leave)
  HyperLogLog → approximate unique viewers during entire session
  Persistent counter → total_joins
  Separate peak counter → peak concurrent viewers

Redis keys (all prefixed with session_id):
  live:{session_id}:participants   SET  — current viewer user IDs
  live:{session_id}:unique         HLL  — HyperLogLog for unique viewers
  live:{session_id}:total_joins    STRING (integer) — total join events
  live:{session_id}:peak           STRING (integer) — peak concurrent count
"""
import logging
from typing import Set

from app.core.observability import LIVE_VIEWERS_CURRENT
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)


class ViewerTracker:
    def _key_participants(self, session_id: str) -> str:
        return f"live:{session_id}:participants"

    def _key_unique(self, session_id: str) -> str:
        return f"live:{session_id}:unique"

    def _key_total_joins(self, session_id: str) -> str:
        return f"live:{session_id}:total_joins"

    def _key_peak(self, session_id: str) -> str:
        return f"live:{session_id}:peak"

    async def participant_joined(self, session_id: str, user_id: str) -> int:
        """
        Register a participant join event.
        Returns updated current viewer count.
        """
        try:
            r = get_redis_client()
            pipe = r.pipeline()
            pipe.sadd(self._key_participants(session_id), user_id)
            pipe.pfadd(self._key_unique(session_id), user_id)
            pipe.incr(self._key_total_joins(session_id))
            await pipe.execute()

            current = await r.scard(self._key_participants(session_id))
            # Update peak if current exceeds stored peak
            peak_raw = await r.get(self._key_peak(session_id))
            peak = int(peak_raw) if peak_raw else 0
            if current > peak:
                await r.set(self._key_peak(session_id), current)

            LIVE_VIEWERS_CURRENT.labels(session_id=session_id).set(current)
            return current
        except Exception as exc:
            logger.debug("viewer_tracker.joined failed: %s", exc)
            return 0

    async def participant_left(self, session_id: str, user_id: str) -> int:
        """Remove participant; returns updated current viewer count."""
        try:
            r = get_redis_client()
            await r.srem(self._key_participants(session_id), user_id)
            current = await r.scard(self._key_participants(session_id))
            LIVE_VIEWERS_CURRENT.labels(session_id=session_id).set(current)
            return current
        except Exception as exc:
            logger.debug("viewer_tracker.left failed: %s", exc)
            return 0

    async def get_current_viewers(self, session_id: str) -> int:
        try:
            r = get_redis_client()
            return await r.scard(self._key_participants(session_id))
        except Exception:
            return 0

    async def get_participant_ids(self, session_id: str) -> Set[str]:
        try:
            r = get_redis_client()
            return await r.smembers(self._key_participants(session_id))
        except Exception:
            return set()

    async def get_peak_viewers(self, session_id: str) -> int:
        try:
            r = get_redis_client()
            val = await r.get(self._key_peak(session_id))
            return int(val) if val else 0
        except Exception:
            return 0

    async def get_unique_viewers(self, session_id: str) -> int:
        """Approximate unique viewer count using HyperLogLog."""
        try:
            r = get_redis_client()
            return await r.pfcount(self._key_unique(session_id))
        except Exception:
            return 0

    async def get_total_joins(self, session_id: str) -> int:
        try:
            r = get_redis_client()
            val = await r.get(self._key_total_joins(session_id))
            return int(val) if val else 0
        except Exception:
            return 0

    async def cleanup(self, session_id: str) -> None:
        """Delete all Redis keys for a session after persisting metrics to DB."""
        try:
            r = get_redis_client()
            await r.delete(
                self._key_participants(session_id),
                self._key_unique(session_id),
                self._key_total_joins(session_id),
                self._key_peak(session_id),
            )
        except Exception as exc:
            logger.debug("viewer_tracker.cleanup failed: %s", exc)


viewer_tracker = ViewerTracker()
