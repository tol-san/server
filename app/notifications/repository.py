import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence, Tuple
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.notifications.models import Notification
from app.users.models import User


class NotificationRepository:
    """Repository handling database operations for Notification entities."""

    async def create(
        self,
        db: AsyncSession,
        *,
        recipient_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        notification_type: str,
        title: str,
        message: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
    ) -> Notification:
        notification = Notification(
            recipient_id=recipient_id,
            actor_id=actor_id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            is_read=False,
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification

    async def get_by_id(
        self, db: AsyncSession, notification_id: uuid.UUID
    ) -> Optional[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.id == notification_id)
            .options(
                selectinload(Notification.actor).selectinload(User.profile),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_notifications(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[Notification], int, int]:
        base_filters = [Notification.recipient_id == user_id]

        # Total unread count
        unread_count_stmt = select(func.count(Notification.id)).where(
            Notification.recipient_id == user_id, Notification.is_read.is_(False)
        )
        unread_count = (await db.execute(unread_count_stmt)).scalar() or 0

        # Query filters
        query_filters = list(base_filters)
        if unread_only:
            query_filters.append(Notification.is_read.is_(False))

        total_stmt = select(func.count(Notification.id)).where(*query_filters)
        total = (await db.execute(total_stmt)).scalar() or 0

        stmt = (
            select(Notification)
            .where(*query_filters)
            .options(
                selectinload(Notification.actor).selectinload(User.profile),
            )
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all(), total, unread_count

    async def get_unread_count(self, db: AsyncSession, user_id: uuid.UUID) -> int:
        stmt = select(func.count(Notification.id)).where(
            Notification.recipient_id == user_id, Notification.is_read.is_(False)
        )
        return (await db.execute(stmt)).scalar() or 0

    async def mark_as_read(
        self, db: AsyncSession, *, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Notification]:
        notification = await self.get_by_id(db, notification_id)
        if not notification or notification.recipient_id != user_id:
            return None

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            db.add(notification)
            await db.commit()
            await db.refresh(notification)

        return notification

    async def mark_all_as_read(self, db: AsyncSession, *, user_id: uuid.UUID) -> int:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(
                Notification.recipient_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=now)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    async def delete(
        self, db: AsyncSession, *, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        notification = await self.get_by_id(db, notification_id)
        if not notification or notification.recipient_id != user_id:
            return False

        await db.delete(notification)
        await db.commit()
        return True


notification_repository = NotificationRepository()
