"""
Community Chat Router.

Endpoints:
  POST  /chats/ws-ticket            — issue short-lived WS ticket
  GET   /chats/{community_id}/messages — paginated history (cursor)
  GET   /chats/{community_id}/presence — online members
  WS    /chats/ws/{community_id}    — WebSocket gateway

WebSocket Auth Flow:
  1. POST /chats/ws-ticket  (Bearer JWT)      → { ticket, expires_in_seconds }
  2. WSS  /chats/ws/{community_id}?ticket=... → connect
  3. ticket consumed (one-time, Redis DEL)
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketState

from app.auth.dependencies import get_current_user
from app.chats.connection_manager import connection_manager
from app.chats.presence import presence_manager
from app.chats.schemas import (
    ChatHistoryResponse,
    PresenceResponse,
    WsEventType,
    WsIncoming,
    WsMessageSendPayload,
    WsOutgoing,
    WsTicketResponse,
)
from app.chats.service import ChatService, chat_service
from app.communities.repository import community_repository
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.observability import CHAT_WS_CONNECTIONS
from app.core.redis import get_redis_client
from app.users.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chats", tags=["Community Chat"])

_HEARTBEAT_INTERVAL = 30  # seconds


# ─────────────────────────────────────────────────────────────────────────────
# WS Ticket Auth
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/ws-ticket", response_model=WsTicketResponse)
async def issue_ws_ticket(
    community_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Issue a short-lived one-time WebSocket ticket for the given community."""
    # Verify membership before issuing ticket
    member = await community_repository.get_membership(
        db, community_id=community_id, user_id=current_user.id
    )
    if not member:
        raise ForbiddenException("You are not a member of this community.")

    ticket = str(uuid.uuid4())
    key = f"ws:ticket:{ticket}"
    payload = json.dumps({"user_id": str(current_user.id), "community_id": str(community_id)})

    r = get_redis_client()
    await r.set(key, payload, ex=settings.WS_TICKET_TTL_SECONDS)

    return WsTicketResponse(
        ticket=ticket,
        expires_in_seconds=settings.WS_TICKET_TTL_SECONDS,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Chat History
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{community_id}/messages", response_model=ChatHistoryResponse)
async def get_chat_history(
    community_id: uuid.UUID,
    before: Optional[str] = Query(None, description="Opaque cursor for pagination"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(lambda: chat_service),
):
    """Fetch message history using cursor/keyset pagination (newest-first)."""
    return await service.get_history(
        db,
        community_id=community_id,
        current_user=current_user,
        before_cursor=before,
        limit=limit,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Presence
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{community_id}/presence", response_model=PresenceResponse)
async def get_presence(
    community_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return online member IDs for a community chat."""
    member = await community_repository.get_membership(
        db, community_id=community_id, user_id=current_user.id
    )
    if not member:
        raise ForbiddenException("You are not a member of this community.")

    user_ids = await presence_manager.get_online_user_ids(str(community_id))
    return PresenceResponse(
        community_id=community_id,
        online_user_ids=list(user_ids),
        online_count=len(user_ids),
    )


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket Gateway
# ─────────────────────────────────────────────────────────────────────────────

@router.websocket("/ws/{community_id}")
async def chat_websocket(
    ws: WebSocket,
    community_id: uuid.UUID,
    ticket: str = Query(..., description="One-time WS ticket from /ws-ticket"),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket gateway for community chat.

    Security:
      - One-time ticket consumed from Redis
      - Community membership enforced
      - Per-user message rate limiting
      - Heartbeat required every 30s
    """
    # 1. Consume WS ticket (one-time use)
    r = get_redis_client()
    ticket_key = f"ws:ticket:{ticket}"
    raw = await r.getdel(ticket_key)
    if not raw:
        await ws.close(code=4001, reason="Invalid or expired ticket")
        return

    ticket_data = json.loads(raw)
    user_id_str = ticket_data["user_id"]
    ticket_community_id = ticket_data["community_id"]

    if ticket_community_id != str(community_id):
        await ws.close(code=4003, reason="Ticket community mismatch")
        return

    # Load full User object (needed for membership check + message creation)
    from app.users.repository import user_repository
    import uuid as _uuid
    current_user = await user_repository.get_by_id(db, _uuid.UUID(user_id_str))
    if not current_user:
        await ws.close(code=4001, reason="User not found")
        return

    # 2. Accept connection
    await ws.accept()

    connection_id = str(uuid.uuid4())
    comm_id_str = str(community_id)
    user_id = user_id_str  # local alias for clarity

    # 3. Register connection
    await connection_manager.connect(
        ws,
        community_id=comm_id_str,
        connection_id=connection_id,
        user_id=user_id,
    )
    await presence_manager.join(comm_id_str, connection_id, user_id)
    CHAT_WS_CONNECTIONS.labels(community_id=comm_id_str).inc()

    # Announce presence
    presence_event = WsOutgoing(
        type=WsEventType.PRESENCE_JOINED,
        payload={"user_id": user_id, "community_id": comm_id_str},
    ).to_json()
    await connection_manager.broadcast_local(comm_id_str, presence_event)

    async def _heartbeat_task():
        """Server-side ping every 30s; closes socket if client stops responding."""
        while ws.client_state == WebSocketState.CONNECTED:
            await asyncio.sleep(_HEARTBEAT_INTERVAL)
            try:
                await ws.send_text(
                    WsOutgoing(type=WsEventType.HEARTBEAT).to_json()
                )
            except Exception:
                break

    hb_task = asyncio.create_task(_heartbeat_task())

    try:
        while True:
            raw_msg = await ws.receive_text()
            try:
                incoming = WsIncoming.model_validate_json(raw_msg)
            except Exception:
                await ws.send_text(
                    WsOutgoing(
                        type=WsEventType.ERROR,
                        payload={"detail": "Invalid message format"},
                    ).to_json()
                )
                continue

            # Route by event type
            if incoming.type == WsEventType.MESSAGE_SEND:
                try:
                    payload = WsMessageSendPayload.model_validate(incoming.payload or {})
                    msg_resp = await chat_service.create_message(
                        db,
                        community_id=community_id,
                        sender=current_user,
                        client_message_id=payload.client_message_id,
                        content=payload.content,
                        reply_to_message_id=payload.reply_to_message_id,
                    )
                    # ACK to sender
                    await ws.send_text(
                        WsOutgoing(
                            type=WsEventType.ACK,
                            request_id=incoming.request_id,
                            payload=msg_resp.model_dump(mode="json"),
                        ).to_json()
                    )
                except Exception as exc:
                    await ws.send_text(
                        WsOutgoing(
                            type=WsEventType.ERROR,
                            request_id=incoming.request_id,
                            payload={"detail": str(exc)},
                        ).to_json()
                    )

            elif incoming.type in (WsEventType.TYPING_START, WsEventType.TYPING_STOP):
                is_typing = incoming.type == WsEventType.TYPING_START
                profile = getattr(current_user, "profile", None)
                username = profile.display_name if profile and profile.display_name else current_user.username
                await chat_service.send_typing(
                    comm_id_str, user_id, username=username, is_typing=is_typing
                )

            elif incoming.type == WsEventType.HEARTBEAT:
                await presence_manager.heartbeat(comm_id_str, connection_id)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WS error for conn %s: %s", connection_id, exc)
    finally:
        hb_task.cancel()
        await connection_manager.disconnect(
            community_id=comm_id_str, connection_id=connection_id
        )
        await presence_manager.leave(comm_id_str, connection_id)
        CHAT_WS_CONNECTIONS.labels(community_id=comm_id_str).dec()

        # Announce departure
        await connection_manager.broadcast_local(
            comm_id_str,
            WsOutgoing(
                type=WsEventType.PRESENCE_LEFT,
                payload={"user_id": user_id, "community_id": comm_id_str},
            ).to_json(),
        )
