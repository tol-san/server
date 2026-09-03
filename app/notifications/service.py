import asyncio
import json
import logging
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.redis import add_to_stream, publish_pubsub, read_from_stream
from app.notifications.models import Notification
from app.notifications.repository import (
    NotificationRepository,
    notification_repository,
)
from app.notifications.schemas import (
    NotificationActor,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
    NotificationResponse,
    PaginatedNotificationsResponse,
    UnreadCountResponse,
)
from app.users.models import User

logger = logging.getLogger(__name__)

# In-memory event queues for real-time fallback in offline / test environments
_in_memory_subscribers: Dict[uuid.UUID, List[asyncio.Queue]] = {}


def map_notification_to_response(n: Notification) -> NotificationResponse:
    actor_item = None
    if n.actor:
        actor_item = NotificationActor(
            id=n.actor.id,
            username=n.actor.username,
            display_name=n.actor.profile.display_name
            if n.actor.profile
            else n.actor.username,
            avatar_url=n.actor.profile.avatar_url if n.actor.profile else None,
        )
    return NotificationResponse(
        id=n.id,
        recipient_id=n.recipient_id,
        actor_id=n.actor_id,
        actor=actor_item,
        notification_type=n.notification_type,
        title=n.title,
        message=n.message,
        entity_type=n.entity_type,
        entity_id=n.entity_id,
        is_read=n.is_read,
        read_at=n.read_at,
        created_at=n.created_at,
    )


class NotificationService:
    """Service handling notification generation, Redis Streams publishing, SSE/WS dispatching, and management."""

    def __init__(self, repo: NotificationRepository = notification_repository):
        self.repo = repo

    async def notify_user(
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
    ) -> NotificationResponse:
        # Don't notify oneself
        if actor_id and actor_id == recipient_id:
            return None  # type: ignore

        # Check recipient notification preferences
        prefs = await self.repo.get_or_create_preferences(db, recipient_id)
        ntype = notification_type.lower()
        if ("like" in ntype or "reaction" in ntype) and not prefs.likes_enabled:
            return None  # type: ignore
        if ("comment" in ntype or "reply" in ntype) and not prefs.comments_enabled:
            return None  # type: ignore
        if ("follow" in ntype) and not prefs.follows_enabled:
            return None  # type: ignore
        if ("mention" in ntype) and not prefs.mentions_enabled:
            return None  # type: ignore
        if ("community" in ntype) and not prefs.community_enabled:
            return None  # type: ignore


        # 1. Persist notification in PostgreSQL
        notification = await self.repo.create(
            db,
            recipient_id=recipient_id,
            actor_id=actor_id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        # Reload with actor
        loaded = await self.repo.get_by_id(db, notification.id)
        resp = map_notification_to_response(loaded or notification)

        # 2. Append event to Redis Stream for durable processing
        stream_payload = {
            "id": str(resp.id),
            "recipient_id": str(resp.recipient_id),
            "actor_id": str(resp.actor_id) if resp.actor_id else "",
            "notification_type": resp.notification_type,
            "title": resp.title,
            "message": resp.message,
            "entity_type": resp.entity_type or "",
            "entity_id": str(resp.entity_id) if resp.entity_id else "",
            "created_at": resp.created_at.isoformat(),
        }
        await add_to_stream(f"stream:notifications:{recipient_id}", stream_payload)
        await add_to_stream("stream:notifications", stream_payload)

        # 3. Broadcast to in-memory active SSE / WebSocket listeners
        if recipient_id in _in_memory_subscribers:
            for q in list(_in_memory_subscribers[recipient_id]):
                try:
                    q.put_nowait(resp.model_dump_json())
                except Exception as exc:
                    logger.debug("Failed to dispatch to in-memory queue: %s", exc)

        # Invalidate cached unread count
        from app.core.cache import cache_service
        await cache_service.delete(f"cache:notif:unread:{recipient_id}")

        return resp

    async def list_notifications(
        self,
        db: AsyncSession,
        current_user: User,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedNotificationsResponse:
        notifications, total, unread_count = await self.repo.get_user_notifications(
            db,
            user_id=current_user.id,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )
        items = [map_notification_to_response(n) for n in notifications]
        return PaginatedNotificationsResponse(
            items=items,
            total=total,
            unread_count=unread_count,
            limit=limit,
            offset=offset,
        )

    async def get_unread_count(
        self, db: AsyncSession, current_user: User
    ) -> UnreadCountResponse:
        from app.core.cache import cache_service
        cache_key = f"cache:notif:unread:{current_user.id}"
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return UnreadCountResponse(unread_count=int(cached))

        count = await self.repo.get_unread_count(db, user_id=current_user.id)
        await cache_service.set(cache_key, count, ttl=300)
        return UnreadCountResponse(unread_count=count)

    async def mark_as_read(
        self, db: AsyncSession, notification_id: uuid.UUID, current_user: User
    ) -> NotificationResponse:
        notification = await self.repo.mark_as_read(
            db, notification_id=notification_id, user_id=current_user.id
        )
        if not notification:
            raise NotFoundException("Notification not found.")

        from app.core.cache import cache_service
        await cache_service.delete(f"cache:notif:unread:{current_user.id}")
        return map_notification_to_response(notification)

    async def mark_all_as_read(
        self, db: AsyncSession, current_user: User
    ) -> Dict[str, Any]:
        count = await self.repo.mark_all_as_read(db, user_id=current_user.id)
        from app.core.cache import cache_service
        await cache_service.set(f"cache:notif:unread:{current_user.id}", 0, ttl=300)
        return {"message": f"Marked {count} notifications as read.", "count": count}

    async def delete_notification(
        self, db: AsyncSession, notification_id: uuid.UUID, current_user: User
    ) -> Dict[str, str]:
        deleted = await self.repo.delete(
            db, notification_id=notification_id, user_id=current_user.id
        )
        if not deleted:
            raise NotFoundException("Notification not found.")
        from app.core.cache import cache_service
        await cache_service.delete(f"cache:notif:unread:{current_user.id}")
        return {"message": "Notification deleted successfully."}


    async def get_preferences(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> NotificationPreferencesResponse:
        prefs = await self.repo.get_or_create_preferences(db, user_id)
        return NotificationPreferencesResponse.model_validate(prefs)

    async def update_preferences(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        payload: NotificationPreferencesUpdateRequest,
    ) -> NotificationPreferencesResponse:
        updates = payload.model_dump(exclude_unset=True)
        prefs = await self.repo.update_preferences(db, user_id, **updates)
        return NotificationPreferencesResponse.model_validate(prefs)

    # --- Real-Time Stream / SSE Generator ---
    async def sse_event_generator(
        self, user_id: uuid.UUID
    ) -> AsyncGenerator[str, None]:
        """Yield Server-Sent Events (SSE) from Redis Stream and in-memory queue."""
        q = asyncio.Queue()
        if user_id not in _in_memory_subscribers:
            _in_memory_subscribers[user_id] = []
        _in_memory_subscribers[user_id].append(q)

        stream_name = f"stream:notifications:{user_id}"
        last_id = "$"

        try:
            # Yield initial connection heartbeat
            yield f"event: ping\ndata: {json.dumps({'status': 'connected'})}\n\n"

            while True:
                # Check Redis Stream for new events
                stream_res = await read_from_stream(
                    stream_name, last_id=last_id, count=5, block_ms=500
                )
                if stream_res:
                    for s_name, entries in stream_res:
                        for entry_id, fields in entries:
                            last_id = entry_id
                            yield f"event: notification\ndata: {json.dumps(fields)}\n\n"

                # Check in-memory queue
                while not q.empty():
                    msg = q.get_nowait()
                    yield f"event: notification\ndata: {msg}\n\n"

                await asyncio.sleep(0.5)
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            if user_id in _in_memory_subscribers:
                if q in _in_memory_subscribers[user_id]:
                    _in_memory_subscribers[user_id].remove(q)
                if not _in_memory_subscribers[user_id]:
                    del _in_memory_subscribers[user_id]

    # --- Ephemeral Signals (Redis Pub/Sub) ---
    async def publish_typing_signal(
        self, user: User, channel: str, is_typing: bool = True
    ) -> None:
        """Publish ephemeral typing indicator via Redis Pub/Sub (fire-and-forget)."""
        payload = json.dumps(
            {
                "type": "typing_indicator",
                "user_id": str(user.id),
                "username": user.username,
                "channel": channel,
                "is_typing": is_typing,
            }
        )
        await publish_pubsub(f"pubsub:typing:{channel}", payload)


notification_service = NotificationService()
