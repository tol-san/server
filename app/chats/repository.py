"""Chat message database operations — keyset pagination, idempotent inserts."""
from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats.models import ChatMessage


def _encode_cursor(created_at: datetime, msg_id: uuid.UUID) -> str:
    raw = json.dumps({"ts": created_at.isoformat(), "id": str(msg_id)})
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> Tuple[datetime, uuid.UUID]:
    raw = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    ts = datetime.fromisoformat(raw["ts"])
    return ts, uuid.UUID(raw["id"])


class ChatRepository:
    async def insert_message(
        self,
        db: AsyncSession,
        *,
        community_id: uuid.UUID,
        sender_id: uuid.UUID,
        client_message_id: uuid.UUID,
        message_type: str,
        content: Optional[str],
        reply_to_message_id: Optional[uuid.UUID],
    ) -> Tuple[ChatMessage, bool]:
        """
        Insert message; return (message, created).
        created=False means the client_message_id already existed (idempotent retry).
        """
        # Check for existing message with same idempotency key
        existing_stmt = select(ChatMessage).where(
            and_(
                ChatMessage.sender_id == sender_id,
                ChatMessage.client_message_id == client_message_id,
            )
        )
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            return existing, False

        now = datetime.now(timezone.utc)
        msg = ChatMessage(
            id=uuid.uuid4(),
            community_id=community_id,
            sender_id=sender_id,
            client_message_id=client_message_id,
            message_type=message_type,
            content=content,
            reply_to_message_id=reply_to_message_id,
            created_at=now,
        )
        db.add(msg)
        await db.flush()
        await db.refresh(msg)
        return msg, True

    async def get_messages_before_cursor(
        self,
        db: AsyncSession,
        *,
        community_id: uuid.UUID,
        before_cursor: Optional[str],
        limit: int = 50,
    ) -> Tuple[List[ChatMessage], Optional[str]]:
        """Cursor-keyset pagination: returns messages newest-first before the cursor."""
        stmt = (
            select(ChatMessage)
            .where(
                and_(
                    ChatMessage.community_id == community_id,
                    ChatMessage.deleted_at.is_(None),
                )
            )
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit + 1)  # fetch one extra to detect has_more
        )

        if before_cursor:
            ts, msg_id = _decode_cursor(before_cursor)
            stmt = stmt.where(
                and_(
                    ChatMessage.community_id == community_id,
                    ChatMessage.deleted_at.is_(None),
                    # (created_at, id) < (cursor_ts, cursor_id)  — keyset
                    (ChatMessage.created_at < ts)
                    | (
                        (ChatMessage.created_at == ts)
                        & (ChatMessage.id < msg_id)
                    ),
                )
            )

        rows = (await db.execute(stmt)).scalars().all()
        has_more = len(rows) > limit
        items = list(rows[:limit])

        next_cursor: Optional[str] = None
        if has_more and items:
            last = items[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)

        return items, next_cursor

    async def soft_delete_message(
        self,
        db: AsyncSession,
        *,
        message_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> Optional[ChatMessage]:
        stmt = select(ChatMessage).where(
            and_(
                ChatMessage.id == message_id,
                ChatMessage.sender_id == actor_id,
                ChatMessage.deleted_at.is_(None),
            )
        )
        msg = (await db.execute(stmt)).scalar_one_or_none()
        if not msg:
            return None
        msg.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        return msg

    async def get_by_id(
        self, db: AsyncSession, message_id: uuid.UUID
    ) -> Optional[ChatMessage]:
        result = await db.execute(
            select(ChatMessage).where(ChatMessage.id == message_id)
        )
        return result.scalar_one_or_none()


chat_repository = ChatRepository()
