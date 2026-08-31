"""Live rooms database operations."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, and_, update as sa_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.live_rooms.models import LiveRoom, LiveSession, ProviderEvent


class LiveRoomRepository:
    async def create(
        self,
        db: AsyncSession,
        *,
        community_id: uuid.UUID,
        created_by: uuid.UUID,
        title: str,
        description: Optional[str],
        provider: str,
        provider_room_name: str,
    ) -> LiveRoom:
        now = datetime.now(timezone.utc)
        room = LiveRoom(
            community_id=community_id,
            created_by=created_by,
            title=title,
            description=description,
            provider=provider,
            provider_room_name=provider_room_name,
            status=LiveRoom.Status.READY,
            created_at=now,
            updated_at=now,
        )
        db.add(room)
        await db.flush()
        await db.refresh(room)
        return room

    async def get_by_id(
        self, db: AsyncSession, room_id: uuid.UUID
    ) -> Optional[LiveRoom]:
        result = await db.execute(
            select(LiveRoom).where(LiveRoom.id == room_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, db: AsyncSession, room_id: uuid.UUID
    ) -> Optional[LiveRoom]:
        result = await db.execute(
            select(LiveRoom).where(LiveRoom.id == room_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_provider_room_name(
        self, db: AsyncSession, provider_room_name: str
    ) -> Optional[LiveRoom]:
        result = await db.execute(
            select(LiveRoom).where(
                LiveRoom.provider_room_name == provider_room_name
            )
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        db: AsyncSession,
        room_id: uuid.UUID,
        status: str,
    ) -> Optional[LiveRoom]:
        room = await self.get_by_id(db, room_id)
        if not room:
            return None
        room.status = status
        room.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return room

    async def update(
        self,
        db: AsyncSession,
        room_id: uuid.UUID,
        **fields,
    ) -> Optional[LiveRoom]:
        room = await self.get_by_id(db, room_id)
        if not room:
            return None
        for k, v in fields.items():
            setattr(room, k, v)
        room.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return room

    async def list_by_community(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> List[LiveRoom]:
        result = await db.execute(
            select(LiveRoom)
            .where(LiveRoom.community_id == community_id)
            .order_by(LiveRoom.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    # ─────────────────────────────────────────────────────────────────────────
    # Sessions
    # ─────────────────────────────────────────────────────────────────────────

    async def create_session(
        self,
        db: AsyncSession,
        *,
        room_id: uuid.UUID,
        host_id: uuid.UUID,
    ) -> LiveSession:
        now = datetime.now(timezone.utc)
        session = LiveSession(
            room_id=room_id,
            host_id=host_id,
            started_at=now,
            created_at=now,
        )
        db.add(session)
        await db.flush()
        await db.refresh(session)
        return session

    async def get_active_session(
        self, db: AsyncSession, room_id: uuid.UUID
    ) -> Optional[LiveSession]:
        result = await db.execute(
            select(LiveSession).where(
                and_(
                    LiveSession.room_id == room_id,
                    LiveSession.ended_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def close_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        *,
        ended_at: datetime,
        duration_seconds: int,
        peak_viewers: int,
        unique_viewers: int,
        total_joins: int,
    ) -> Optional[LiveSession]:
        result = await db.execute(
            select(LiveSession).where(LiveSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return None
        session.ended_at = ended_at
        session.duration_seconds = duration_seconds
        session.peak_viewers = peak_viewers
        session.unique_viewers = unique_viewers
        session.total_joins = total_joins
        await db.flush()
        return session

    # ─────────────────────────────────────────────────────────────────────────
    # Webhook idempotency
    # ─────────────────────────────────────────────────────────────────────────

    async def try_store_provider_event(
        self,
        db: AsyncSession,
        *,
        provider: str,
        provider_event_id: str,
        event_type: str,
    ) -> bool:
        """
        INSERT event into provider_events if not already seen.
        Returns True if newly inserted (process it), False if duplicate (skip).
        """
        # Check for duplicate
        result = await db.execute(
            select(ProviderEvent).where(
                and_(
                    ProviderEvent.provider == provider,
                    ProviderEvent.provider_event_id == provider_event_id,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing.processed_at is None

        now = datetime.now(timezone.utc)
        event = ProviderEvent(
            provider=provider,
            provider_event_id=provider_event_id,
            event_type=event_type,
            received_at=now,
            processed_at=None,
        )
        try:
            async with db.begin_nested():
                db.add(event)
                await db.flush()
            return True
        except IntegrityError:
            return False

    async def mark_provider_event_processed(
        self, db: AsyncSession, *, provider: str, provider_event_id: str
    ) -> None:
        event = (
            await db.execute(
                select(ProviderEvent).where(
                    ProviderEvent.provider == provider,
                    ProviderEvent.provider_event_id == provider_event_id,
                )
            )
        ).scalar_one_or_none()
        if event:
            event.processed_at = datetime.now(timezone.utc)
            await db.flush()


live_room_repository = LiveRoomRepository()
