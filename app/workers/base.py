"""
Base Redis Streams consumer with:
  - Consumer group management (auto-create group + XAUTOCLAIM)
  - Per-event retry tracking
  - Dead-letter after WORKER_MAX_RETRIES failures
  - Prometheus metrics per worker + event type
  - Structured logging with trace ID
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.observability import (
    DEAD_LETTER_EVENTS_TOTAL,
    WORKER_EVENT_DURATION,
    WORKER_EVENTS_FAILED,
    WORKER_EVENTS_PROCESSED,
)
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Redis Stream name constants
# ─────────────────────────────────────────────────────────────────────────────
STREAM_CHAT = "stream:chat:events"
STREAM_LIVE = "stream:live:events"
STREAM_GENERAL = "stream:general:events"

# Shared database session factory for workers
_sessionmaker = None


def _get_sessionmaker():
    global _sessionmaker
    if _sessionmaker is None:
        from app.core.database import AsyncSessionLocal
        _sessionmaker = AsyncSessionLocal
    return _sessionmaker


class BaseStreamConsumer(ABC):
    """
    Abstract Redis Streams consumer with retry, dead-letter, and observability.

    Subclasses implement:
      - stream_name:   Redis Stream key to consume from
      - group_name:    Consumer group name
      - worker_name:   Human-readable label for metrics/logs
      - handle_event:  Process one event payload (dict)
    """

    stream_name: str = ""
    group_name: str = ""
    worker_name: str = "worker"
    consumer_name: str = ""

    def __init__(self):
        self.consumer_name = f"{self.worker_name}-{uuid.uuid4().hex[:6]}"
        self._running = False

    # ─────────────────────────────────────────────────────────────────────────
    # Abstract interface
    # ─────────────────────────────────────────────────────────────────────────

    @abstractmethod
    async def handle_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Process a single event. Raise an exception to signal failure.
        The base class handles retries and dead-lettering.
        """
        ...

    # ─────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Run the consumer loop. Call as an asyncio task."""
        self._running = True
        await self._ensure_consumer_group()
        logger.info(
            "[%s] Consumer started — stream=%s group=%s consumer=%s",
            self.worker_name,
            self.stream_name,
            self.group_name,
            self.consumer_name,
        )
        while self._running:
            try:
                await self._poll_and_process()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("[%s] Unexpected error in poll loop: %s", self.worker_name, exc)
                await asyncio.sleep(2)

    async def stop(self) -> None:
        self._running = False

    # ─────────────────────────────────────────────────────────────────────────
    # Core polling loop
    # ─────────────────────────────────────────────────────────────────────────

    async def _ensure_consumer_group(self) -> None:
        try:
            r = get_redis_client()
            await r.xgroup_create(self.stream_name, self.group_name, id="0", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" in str(exc):
                pass  # Group already exists
            else:
                logger.warning("[%s] Could not create consumer group: %s", self.worker_name, exc)

    async def _poll_and_process(self) -> None:
        r = get_redis_client()
        try:
            results = await r.xreadgroup(
                groupname=self.group_name,
                consumername=self.consumer_name,
                streams={self.stream_name: ">"},
                count=10,
                block=settings.WORKER_BLOCK_MS,
            )
        except Exception as exc:
            logger.debug("[%s] xreadgroup failed: %s", self.worker_name, exc)
            await asyncio.sleep(1)
            return

        if not results:
            return

        for _stream, messages in results:
            for msg_id, fields in messages:
                await self._process_message(r, msg_id, fields)

    async def _process_message(self, r, msg_id: str, fields: Dict[str, str]) -> None:
        event_type = fields.get("event_type", "unknown")
        payload_raw = fields.get("payload", "{}")
        retry_count = int(fields.get("_retry_count", "0"))

        try:
            payload = json.loads(payload_raw)
        except Exception:
            payload = {"raw": payload_raw}

        start = time.perf_counter()
        try:
            await self.handle_event(event_type, payload)
            duration = time.perf_counter() - start

            # ACK on success
            await r.xack(self.stream_name, self.group_name, msg_id)
            WORKER_EVENTS_PROCESSED.labels(
                worker=self.worker_name, event_type=event_type
            ).inc()
            WORKER_EVENT_DURATION.labels(
                worker=self.worker_name, event_type=event_type
            ).observe(duration)

        except Exception as exc:
            duration = time.perf_counter() - start
            WORKER_EVENTS_FAILED.labels(
                worker=self.worker_name, event_type=event_type
            ).inc()

            if retry_count >= settings.WORKER_MAX_RETRIES:
                # Move to dead-letter
                logger.error(
                    "[%s] Moving event to dead-letter after %d retries: event_type=%s error=%s",
                    self.worker_name,
                    retry_count,
                    event_type,
                    exc,
                )
                await self._send_to_dead_letter(
                    event_type=event_type,
                    payload=payload,
                    error_message=str(exc),
                    retry_count=retry_count,
                    fields=fields,
                )
                await r.xack(self.stream_name, self.group_name, msg_id)
                DEAD_LETTER_EVENTS_TOTAL.labels(
                    worker=self.worker_name, event_type=event_type
                ).inc()
            else:
                # Re-publish with incremented retry count
                logger.warning(
                    "[%s] Event failed (retry %d/%d): event_type=%s error=%s",
                    self.worker_name,
                    retry_count + 1,
                    settings.WORKER_MAX_RETRIES,
                    event_type,
                    exc,
                )
                new_fields = dict(fields)
                new_fields["_retry_count"] = str(retry_count + 1)
                await r.xadd(self.stream_name, new_fields)
                await r.xack(self.stream_name, self.group_name, msg_id)

    async def _send_to_dead_letter(
        self,
        *,
        event_type: str,
        payload: Dict[str, Any],
        error_message: str,
        retry_count: int,
        fields: Dict[str, str],
    ) -> None:
        """Persist dead-letter event to PostgreSQL dead_letter_events table."""
        try:
            async with _get_sessionmaker()() as db:
                from app.core.outbox import DeadLetterEvent
                dl = DeadLetterEvent(
                    source_event_id=uuid.UUID(fields.get("outbox_event_id", str(uuid.uuid4()))),
                    aggregate_type=fields.get("aggregate_type", "unknown"),
                    aggregate_id=fields.get("aggregate_id", ""),
                    event_type=event_type,
                    payload=json.dumps(payload, default=str),
                    error_message=error_message,
                    retry_count=retry_count,
                    worker=self.worker_name,
                )
                db.add(dl)
                await db.commit()
        except Exception as exc:
            logger.error("[%s] Failed to write dead-letter event: %s", self.worker_name, exc)
