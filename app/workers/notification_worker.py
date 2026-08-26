"""
Notification Worker — consumes chat and live stream events from Redis Streams
and creates in-app notifications via the existing notify_user service.

Handles:
  chat.message.created         → notify mentioned users / reply recipients
  live_room.session_started    → notify community followers that stream is live
  live_room.session_ended      → (optional) analytics notification
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from app.workers.base import BaseStreamConsumer, STREAM_CHAT, STREAM_LIVE

logger = logging.getLogger(__name__)


class ChatNotificationWorker(BaseStreamConsumer):
    stream_name = STREAM_CHAT
    group_name = "notification-worker:chat"
    worker_name = "notification-chat"

    async def handle_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == "chat.message.created":
            await self._handle_chat_message(payload)

    async def _handle_chat_message(self, payload: Dict[str, Any]) -> None:
        """
        For now: notify reply recipients.
        Future: parse @mentions and notify tagged users.
        """
        # Currently a no-op stub — extend to notify reply_to sender
        message_id = payload.get("message_id")
        sender_id = payload.get("sender_id")
        community_id = payload.get("community_id")
        logger.debug(
            "[notification-chat] Message event: msg=%s sender=%s community=%s",
            message_id, sender_id, community_id
        )
        # Future: detect @mentions, use notify_user from notifications.service


class LiveNotificationWorker(BaseStreamConsumer):
    stream_name = STREAM_LIVE
    group_name = "notification-worker:live"
    worker_name = "notification-live"

    async def handle_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == "live_room.session_started":
            await self._handle_session_started(payload)

    async def _handle_session_started(self, payload: Dict[str, Any]) -> None:
        """
        Notify community members that a live session has started.
        """
        from app.core.database import AsyncSessionLocal
        from app.notifications.service import notification_service

        room_id = payload.get("room_id")
        community_id = payload.get("community_id")
        host_id = payload.get("host_id")

        logger.info(
            "[notification-live] Session started: room=%s community=%s host=%s",
            room_id, community_id, host_id
        )

        # Notify community members
        try:
            from sqlalchemy import select
            from app.communities.models import CommunityMembership
            import uuid

            async with AsyncSessionLocal() as db:
                stmt = select(CommunityMembership).where(
                    CommunityMembership.community_id == uuid.UUID(community_id)
                )
                memberships = (await db.execute(stmt)).scalars().all()
                for m in memberships:
                    if str(m.user_id) != host_id:
                        await notification_service.notify_user(
                            db,
                            recipient_id=m.user_id,
                            actor_id=uuid.UUID(host_id),
                            notification_type="live_started",
                            entity_type="live_room",
                            entity_id=uuid.UUID(room_id),
                            title="Live stream started",
                            message="A live session started in your community",
                        )
        except Exception as exc:
            logger.error("[notification-live] Failed to send live notifications: %s", exc)
            raise


chat_notification_worker = ChatNotificationWorker()
live_notification_worker = LiveNotificationWorker()
