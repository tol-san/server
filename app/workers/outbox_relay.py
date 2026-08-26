"""
Outbox Relay Worker — polls outbox_events, publishes to Redis Streams.

Guarantees:
  1. Reads batches of unpublished outbox_events ordered by created_at
  2. XADDs each event to the appropriate Redis Stream
  3. Marks event as published_at (idempotent via published_at IS NULL filter)
  4. Updates Prometheus gauge for pending outbox events

Stream routing:
  aggregate_type="chat_message"  → stream:chat:events
  aggregate_type="live_*"        → stream:live:events
  default                        → stream:general:events
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import select, update

from app.core.config import settings
from app.core.observability import OUTBOX_EVENTS_PENDING
from app.core.redis import get_redis_client
from app.workers.base import STREAM_CHAT, STREAM_LIVE, STREAM_GENERAL

logger = logging.getLogger(__name__)


def _route_stream(aggregate_type: str) -> str:
    if aggregate_type == "chat_message":
        return STREAM_CHAT
    if aggregate_type.startswith("live"):
        return STREAM_LIVE
    return STREAM_GENERAL


class OutboxRelayWorker:
    """Polls outbox_events table and publishes each event to Redis Streams."""

    def __init__(self):
        self._running = False

    async def start(self) -> None:
        self._running = True
        logger.info("[outbox-relay] Started — poll_interval=%.1fs", settings.OUTBOX_POLL_INTERVAL_SECONDS)
        while self._running:
            try:
                await self._relay_batch()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("[outbox-relay] Error: %s", exc)
            await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL_SECONDS)

    async def stop(self) -> None:
        self._running = False

    async def _relay_batch(self) -> None:
        from app.core.database import AsyncSessionLocal
        from app.core.outbox import OutboxEvent

        async with AsyncSessionLocal() as db:
            # Fetch unpublished events
            stmt = (
                select(OutboxEvent)
                .where(OutboxEvent.published_at.is_(None))
                .order_by(OutboxEvent.created_at.asc())
                .limit(settings.OUTBOX_BATCH_SIZE)
                .with_for_update(skip_locked=True)  # concurrent-safe
            )
            result = await db.execute(stmt)
            events = result.scalars().all()

            if not events:
                # Update pending gauge
                try:
                    r = get_redis_client()
                    OUTBOX_EVENTS_PENDING.set(0)
                except Exception:
                    pass
                return

            r = get_redis_client()
            published_ids = []

            for event in events:
                try:
                    stream = _route_stream(event.aggregate_type)
                    fields = {
                        "outbox_event_id": str(event.id),
                        "event_type": event.event_type,
                        "aggregate_type": event.aggregate_type,
                        "aggregate_id": event.aggregate_id,
                        "payload": event.payload,
                        "_retry_count": "0",
                    }
                    await r.xadd(stream, fields)
                    published_ids.append(event.id)
                except Exception as exc:
                    logger.warning(
                        "[outbox-relay] Failed to publish event %s: %s", event.id, exc
                    )

            # Mark as published
            if published_ids:
                now = datetime.now(timezone.utc)
                await db.execute(
                    update(OutboxEvent)
                    .where(OutboxEvent.id.in_(published_ids))
                    .values(published_at=now)
                )
                await db.commit()

            OUTBOX_EVENTS_PENDING.set(len(events) - len(published_ids))
            logger.debug(
                "[outbox-relay] Published %d/%d events", len(published_ids), len(events)
            )


outbox_relay_worker = OutboxRelayWorker()
