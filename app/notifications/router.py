import asyncio
import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.core.config import settings
from app.core.redis import get_redis_client
from app.core.exceptions import BadRequestException, ForbiddenException
from app.communities.repository import community_repository
from app.chats.schemas import WsTicketResponse
from app.notifications.schemas import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
    NotificationResponse,
    PaginatedNotificationsResponse,
    TypingIndicatorPayload,
    UnreadCountResponse,
)
from app.notifications.service import (
    NotificationService,
    _in_memory_subscribers,
    notification_service,
)
from app.users.models import User
from app.users.repository import user_repository

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/ws-ticket", response_model=WsTicketResponse)
async def issue_notification_ws_ticket(
    current_user: User = Depends(get_current_active_user),
):
    ticket = str(uuid.uuid4())
    await get_redis_client().set(
        f"ws:notification-ticket:{ticket}",
        json.dumps({"user_id": str(current_user.id)}),
        ex=settings.WS_TICKET_TTL_SECONDS,
    )
    return WsTicketResponse(
        ticket=ticket, expires_in_seconds=settings.WS_TICKET_TTL_SECONDS
    )


@router.get(
    "",
    response_model=PaginatedNotificationsResponse,
    status_code=status.HTTP_200_OK,
    summary="List notifications",
    description="Retrieve paginated list of user notifications, with optional unread_only filter.",
)
async def list_notifications(
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(lambda: notification_service),
) -> PaginatedNotificationsResponse:
    return await service.list_notifications(
        db, current_user, unread_only=unread_only, limit=limit, offset=offset
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get unread notification count",
    description="Retrieve the total count of unread notifications for badge counters.",
)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(lambda: notification_service),
) -> UnreadCountResponse:
    return await service.get_unread_count(db, current_user)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark notification as read",
    description="Mark an individual notification as read.",
)
async def mark_as_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(lambda: notification_service),
) -> NotificationResponse:
    return await service.mark_as_read(db, notification_id, current_user)


@router.post(
    "/read-all",
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read",
    description="Mark all unread notifications for the current user as read.",
)
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(lambda: notification_service),
):
    return await service.mark_all_as_read(db, current_user)


@router.get(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user notification preferences",
    description="Retrieve in-app, push, and quiet hours notification preferences for the authenticated user.",
)
async def get_notification_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(lambda: notification_service),
) -> NotificationPreferencesResponse:
    return await service.get_preferences(db, current_user.id)


@router.patch(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user notification preferences",
    description="Update notification preference toggles for likes, comments, follows, mentions, community events, push, or quiet hours.",
)
async def update_notification_preferences(
    payload: NotificationPreferencesUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(lambda: notification_service),
) -> NotificationPreferencesResponse:
    return await service.update_preferences(db, current_user.id, payload)


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete notification",
    description="Remove a notification from user history.",
)
async def delete_notification(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(lambda: notification_service),
):
    return await service.delete_notification(db, notification_id, current_user)


# --- Server-Sent Events (SSE) Stream ---
@router.get(
    "/stream",
    summary="Server-Sent Events (SSE) real-time notification stream",
    description="Establish persistent SSE stream for real-time notification events powered by Redis Streams.",
)
async def notification_sse_stream(
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(lambda: notification_service),
):
    return StreamingResponse(
        service.sse_event_generator(current_user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# --- Ephemeral Signals (Redis Pub/Sub) ---
@router.post(
    "/typing",
    status_code=status.HTTP_200_OK,
    summary="Publish ephemeral typing indicator (Redis Pub/Sub)",
    description="Broadcast a lightweight fire-and-forget typing status to chat channels via Redis Pub/Sub.",
)
async def publish_typing(
    payload: TypingIndicatorPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(lambda: notification_service),
):
    try:
        community_id = uuid.UUID(payload.channel)
    except ValueError as exc:
        raise BadRequestException("Typing channel must be a community ID.") from exc
    membership = await community_repository.get_membership(
        db, community_id, current_user.id
    )
    if not membership:
        raise ForbiddenException("You are not a member of this community.")
    await service.publish_typing_signal(
        user=current_user,
        channel=payload.channel,
        is_typing=payload.is_typing,
    )
    return {"status": "ok", "channel": payload.channel}


# --- WebSocket Endpoint for Live Notifications & Presence ---
@router.websocket("/ws")
async def notification_websocket(
    websocket: WebSocket,
    ticket: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Real-time WebSocket endpoint for live notification updates and client signals."""
    if not ticket:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        raw = await get_redis_client().getdel(f"ws:notification-ticket:{ticket}")
        if not raw:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        ticket_payload = json.loads(raw)
        user_id_str = ticket_payload.get("user_id")
        user_id = uuid.UUID(user_id_str)
        user = await user_repository.get_by_id(db, user_id)
        if not user or not user.is_active:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    # Register user in-memory queue
    q = asyncio.Queue()
    if user_id not in _in_memory_subscribers:
        _in_memory_subscribers[user_id] = []
    _in_memory_subscribers[user_id].append(q)

    # Welcome message
    await websocket.send_json(
        {
            "event": "connected",
            "message": f"Connected to notifications stream as {user.username}",
        }
    )

    async def sender_loop():
        try:
            while True:
                msg = await q.get()
                await websocket.send_text(msg)
        except Exception:
            pass

    sender_task = asyncio.create_task(sender_loop())

    try:
        while True:
            # Listen for client messages (e.g. ping, typing signals)
            data = await websocket.receive_text()
            try:
                parsed = json.loads(data)
                if parsed.get("action") == "ping":
                    await websocket.send_json({"event": "pong"})
            except Exception:
                pass
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        sender_task.cancel()
        if user_id in _in_memory_subscribers:
            if q in _in_memory_subscribers[user_id]:
                _in_memory_subscribers[user_id].remove(q)
            if not _in_memory_subscribers[user_id]:
                del _in_memory_subscribers[user_id]
