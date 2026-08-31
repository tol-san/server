"""
Community Chat Service — business logic layer.

Message flow (Production MVP):
  1. Validate membership
  2. Rate-limit check (Redis)
  3. INSERT PostgreSQL (idempotent on client_message_id)
  4. INSERT outbox_events in same transaction
  5. COMMIT
  6. PUBLISH Redis Pub/Sub (fan-out to WS connections on all workers)
  7. Return ChatMessageResponse
"""
from __future__ import annotations

import json
import uuid
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.chats.models import ChatMessage
from app.chats.repository import ChatRepository, chat_repository
from app.chats.schemas import (
    ChatMessageResponse,
    ChatHistoryResponse,
    MessageType,
    SenderInfo,
    WsEventType,
    WsOutgoing,
)
from app.communities.repository import CommunityRepository, community_repository
from app.core.config import settings
from app.core.exceptions import ForbiddenException, BadRequestException
from app.core.outbox import publish as outbox_publish
from app.core.redis import get_redis_client, publish_pubsub
from app.users.models import User
from app.core.observability import CHAT_MESSAGES_TOTAL, CHAT_MESSAGES_RATE_LIMITED

logger = logging.getLogger(__name__)


def _map_message(msg: ChatMessage) -> ChatMessageResponse:
    sender = msg.sender
    profile = getattr(sender, "profile", None)
    return ChatMessageResponse(
        id=msg.id,
        community_id=msg.community_id,
        sender=SenderInfo(
            id=sender.id,
            username=sender.username,
            display_name=(profile.display_name if profile and profile.display_name else sender.username),
            avatar_url=profile.avatar_url if profile else None,
        ),
        client_message_id=msg.client_message_id,
        message_type=MessageType(msg.message_type),
        content=None if msg.is_deleted else msg.content,
        reply_to_message_id=msg.reply_to_message_id,
        created_at=msg.created_at,
        edited_at=msg.edited_at,
        is_deleted=msg.is_deleted,
    )


class ChatService:
    def __init__(
        self,
        repo: ChatRepository = chat_repository,
        comm_repo: CommunityRepository = community_repository,
    ):
        self.repo = repo
        self.comm_repo = comm_repo

    # ─────────────────────────────────────────────────────────────────────────
    # Rate Limiting (Redis sliding counter)
    # ─────────────────────────────────────────────────────────────────────────

    async def _check_rate_limit(self, user_id: str) -> None:
        key = f"ratelimit:chat:{user_id}"
        try:
            r = get_redis_client()
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, settings.CHAT_RATE_LIMIT_WINDOW_SECONDS)
            results = await pipe.execute()
            count = results[0]
            if count > settings.CHAT_RATE_LIMIT_MESSAGES:
                CHAT_MESSAGES_RATE_LIMITED.labels(user_id=user_id).inc()
                raise BadRequestException(
                    f"Rate limit exceeded: max {settings.CHAT_RATE_LIMIT_MESSAGES} "
                    f"messages per {settings.CHAT_RATE_LIMIT_WINDOW_SECONDS}s."
                )
        except BadRequestException:
            raise
        except Exception as exc:
            logger.debug("Rate limit check failed (skipping): %s", exc)

    # ─────────────────────────────────────────────────────────────────────────
    # Create Message
    # ─────────────────────────────────────────────────────────────────────────

    async def create_message(
        self,
        db: AsyncSession,
        *,
        community_id: uuid.UUID,
        sender: User,
        client_message_id: uuid.UUID,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        reply_to_message_id: Optional[uuid.UUID] = None,
    ) -> ChatMessageResponse:
        # 1. Membership verification
        member = await self.comm_repo.get_membership(
            db, community_id=community_id, user_id=sender.id
        )
        if not member:
            raise ForbiddenException("You are not a member of this community.")

        if reply_to_message_id:
            reply = await self.repo.get_by_id(db, reply_to_message_id)
            if (
                not reply
                or reply.community_id != community_id
                or reply.deleted_at is not None
            ):
                raise BadRequestException("Reply target is not a message in this community.")

        # 2. Rate limit
        await self._check_rate_limit(str(sender.id))

        # 3. Insert message + outbox event atomically
        async with db.begin_nested():
            msg, created = await self.repo.insert_message(
                db,
                community_id=community_id,
                sender_id=sender.id,
                client_message_id=client_message_id,
                message_type=message_type.value,
                content=content,
                reply_to_message_id=reply_to_message_id,
            )
            if created:
                await outbox_publish(
                    db,
                    event_type="chat.message.created",
                    aggregate_type="chat_message",
                    aggregate_id=str(msg.id),
                    payload={
                        "message_id": str(msg.id),
                        "community_id": str(community_id),
                        "sender_id": str(sender.id),
                        "content": content,
                        "message_type": message_type.value,
                        "created_at": msg.created_at.isoformat(),
                    },
                )

        await db.commit()
        resp = _map_message(msg)

        # 4. Publish to Redis Pub/Sub for real-time fan-out (after DB commit)
        if created:
            CHAT_MESSAGES_TOTAL.labels(community_id=str(community_id)).inc()
            ws_event = WsOutgoing(
                type=WsEventType.MESSAGE_CREATED,
                payload=resp.model_dump(mode="json"),
            )
            await publish_pubsub(
                f"pubsub:chat:{community_id}", ws_event.to_json()
            )

        return resp

    # ─────────────────────────────────────────────────────────────────────────
    # History (cursor pagination)
    # ─────────────────────────────────────────────────────────────────────────

    async def get_history(
        self,
        db: AsyncSession,
        *,
        community_id: uuid.UUID,
        current_user: User,
        before_cursor: Optional[str] = None,
        limit: int = 50,
    ) -> ChatHistoryResponse:
        member = await self.comm_repo.get_membership(
            db, community_id=community_id, user_id=current_user.id
        )
        if not member:
            raise ForbiddenException("You are not a member of this community.")

        messages, next_cursor = await self.repo.get_messages_before_cursor(
            db, community_id=community_id, before_cursor=before_cursor, limit=limit
        )
        return ChatHistoryResponse(
            items=[_map_message(m) for m in messages],
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Typing indicators (ephemeral Pub/Sub)
    # ─────────────────────────────────────────────────────────────────────────

    async def send_typing(
        self,
        community_id: str,
        user_id: str,
        username: str,
        is_typing: bool,
    ) -> None:
        event = WsOutgoing(
            type=WsEventType.TYPING_START if is_typing else WsEventType.TYPING_STOP,
            payload={"user_id": user_id, "username": username},
        )
        await publish_pubsub(
            f"pubsub:chat:{community_id}:typing", event.to_json()
        )


chat_service = ChatService()
