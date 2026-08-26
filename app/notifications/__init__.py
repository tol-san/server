"""Notifications module providing event-driven alerts, Redis Streams, SSE, and WebSocket delivery."""

from app.notifications.models import Notification
from app.notifications.repository import (
    NotificationRepository,
    notification_repository,
)
from app.notifications.router import router as notifications_router
from app.notifications.schemas import (
    NotificationActor,
    NotificationResponse,
    PaginatedNotificationsResponse,
    TypingIndicatorPayload,
    UnreadCountResponse,
)
from app.notifications.service import (
    NotificationService,
    notification_service,
)

__all__ = [
    "Notification",
    "NotificationRepository",
    "notification_repository",
    "NotificationService",
    "notification_service",
    "notifications_router",
    "NotificationActor",
    "NotificationResponse",
    "PaginatedNotificationsResponse",
    "UnreadCountResponse",
    "TypingIndicatorPayload",
]
