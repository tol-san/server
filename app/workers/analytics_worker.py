"""
Analytics Worker — consumes stream events and updates counters / metrics.

Handles:
  chat.message.created         → increment community chat_message_count
  live_room.session_started    → record session start time
  live_room.session_ended      → log final viewer metrics
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from app.workers.base import BaseStreamConsumer, STREAM_CHAT, STREAM_LIVE

logger = logging.getLogger(__name__)


class ChatAnalyticsWorker(BaseStreamConsumer):
    stream_name = STREAM_CHAT
    group_name = "analytics-worker:chat"
    worker_name = "analytics-chat"

    async def handle_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == "chat.message.created":
            await self._increment_message_count(payload)

    async def _increment_message_count(self, payload: Dict[str, Any]) -> None:
        community_id = payload.get("community_id", "unknown")
        # Atomic Redis counter for high-frequency chat analytics
        try:
            from app.core.redis import get_redis_client
            r = get_redis_client()
            await r.incr(f"analytics:chat:{community_id}:message_count")
        except Exception as exc:
            logger.debug("[analytics-chat] Redis increment failed: %s", exc)
        logger.debug(
            "[analytics-chat] Incremented message count for community %s", community_id
        )


class LiveAnalyticsWorker(BaseStreamConsumer):
    stream_name = STREAM_LIVE
    group_name = "analytics-worker:live"
    worker_name = "analytics-live"

    async def handle_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == "live_room.session_ended":
            await self._log_session_metrics(payload)

    async def _log_session_metrics(self, payload: Dict[str, Any]) -> None:
        session_id = payload.get("session_id")
        duration = payload.get("duration_seconds", 0)
        peak = payload.get("peak_viewers", 0)
        unique = payload.get("unique_viewers", 0)
        total_joins = payload.get("total_joins", 0)

        logger.info(
            "[analytics-live] Session ended: session=%s duration=%ds peak=%d unique=%d total_joins=%d",
            session_id, duration, peak, unique, total_joins
        )

        # Future: write to analytics DB table, BigQuery, etc.


chat_analytics_worker = ChatAnalyticsWorker()
live_analytics_worker = LiveAnalyticsWorker()
