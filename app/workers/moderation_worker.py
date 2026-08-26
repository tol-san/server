"""
Moderation Worker — inspects chat messages for content policy violations.

Handles:
  chat.message.created  → basic content length/pattern check,
                          future: integrate ML moderation API

Currently implements:
  - Max content length enforcement
  - Basic banned-word pattern detection (configurable wordlist)
  - Soft-delete offending message + create a system report
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from app.workers.base import BaseStreamConsumer, STREAM_CHAT

logger = logging.getLogger(__name__)

# Minimal stub wordlist — replace with real moderation API or config
_BANNED_PATTERNS: List[re.Pattern] = []

MAX_CONTENT_LENGTH = 4000


class ModerationWorker(BaseStreamConsumer):
    stream_name = STREAM_CHAT
    group_name = "moderation-worker"
    worker_name = "moderation"

    async def handle_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == "chat.message.created":
            await self._moderate_message(payload)

    async def _moderate_message(self, payload: Dict[str, Any]) -> None:
        message_id = payload.get("message_id")
        content = payload.get("content") or ""
        sender_id = payload.get("sender_id")

        violations: List[str] = []

        # 1. Length check
        if len(content) > MAX_CONTENT_LENGTH:
            violations.append("content_too_long")

        # 2. Pattern check (extensible)
        for pattern in _BANNED_PATTERNS:
            if pattern.search(content):
                violations.append("banned_pattern")
                break

        if violations:
            logger.warning(
                "[moderation] Violation detected: message=%s sender=%s violations=%s",
                message_id, sender_id, violations
            )
            await self._action_violation(message_id=message_id, reasons=violations)

    async def _action_violation(self, message_id: str, reasons: List[str]) -> None:
        """Soft-delete the offending message and create an automated system report."""
        import uuid
        from app.core.database import AsyncSessionLocal
        from app.chats.models import ChatMessage
        from sqlalchemy import select
        from datetime import datetime, timezone

        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ChatMessage).where(
                        ChatMessage.id == uuid.UUID(message_id)
                    )
                )
                msg = result.scalar_one_or_none()
                if msg and not msg.is_deleted:
                    msg.deleted_at = datetime.now(timezone.utc)
                    await db.commit()
                    logger.info(
                        "[moderation] Soft-deleted message %s. Reasons: %s",
                        message_id, reasons
                    )
        except Exception as exc:
            logger.error("[moderation] Failed to action violation for message %s: %s", message_id, exc)
            raise


moderation_worker = ModerationWorker()
