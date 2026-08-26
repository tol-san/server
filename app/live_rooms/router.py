"""
Live Streaming Rooms Router.

Endpoints:
  POST   /live-rooms                              — create room (owner/moderator)
  GET    /live-rooms/{room_id}                    — room detail + current viewers
  PATCH  /live-rooms/{room_id}                    — update title/description
  POST   /live-rooms/{room_id}/start              — start session, get host token
  POST   /live-rooms/{room_id}/end               — end session, persist metrics
  POST   /live-rooms/{room_id}/token             — get viewer token
  GET    /live-rooms/{room_id}/metrics           — live/historic metrics
  POST   /live-rooms/{room_id}/reconcile         — manual reconciliation (admin)
  POST   /live-rooms/webhooks/livekit            — LiveKit webhook receiver
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_current_active_superuser
from app.core.database import get_db
from app.live_rooms.schemas import (
    LiveMetricsResponse,
    LiveRoomCreate,
    LiveRoomResponse,
    LiveRoomUpdate,
    LiveSessionResponse,
    LiveTokenResponse,
)
from app.live_rooms.service import LiveRoomService, live_room_service
from app.users.models import User

router = APIRouter(prefix="/live-rooms", tags=["Live Streaming"])


@router.post("", response_model=LiveRoomResponse, status_code=201)
async def create_live_room(
    community_id: uuid.UUID,
    payload: LiveRoomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: LiveRoomService = Depends(lambda: live_room_service),
):
    """Create a live room for a community (owner/moderator only)."""
    return await service.create_room(
        db, community_id=community_id, current_user=current_user, payload=payload
    )


@router.get("/{room_id}", response_model=LiveRoomResponse)
async def get_live_room(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: LiveRoomService = Depends(lambda: live_room_service),
):
    """Get live room details including current viewer count."""
    return await service.get_room(db, room_id, current_user)


@router.patch("/{room_id}", response_model=LiveRoomResponse)
async def update_live_room(
    room_id: uuid.UUID,
    payload: LiveRoomUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: LiveRoomService = Depends(lambda: live_room_service),
):
    """Update live room title or description."""
    return await service.update_room(db, room_id, current_user, payload)


@router.post("/{room_id}/start", response_model=LiveTokenResponse)
async def start_live_session(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: LiveRoomService = Depends(lambda: live_room_service),
):
    """Start a live session. Returns host token for LiveKit connection."""
    return await service.start_session(db, room_id, current_user)


@router.post("/{room_id}/end", response_model=LiveSessionResponse)
async def end_live_session(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: LiveRoomService = Depends(lambda: live_room_service),
):
    """End the active live session. Persists final metrics to PostgreSQL."""
    return await service.end_session(db, room_id, current_user)


@router.post("/{room_id}/token", response_model=LiveTokenResponse)
async def get_viewer_token(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: LiveRoomService = Depends(lambda: live_room_service),
):
    """Request a viewer token for an active live room. Viewer count is updated via webhook."""
    return await service.request_viewer_token(db, room_id, current_user)


@router.get("/{room_id}/metrics", response_model=LiveMetricsResponse)
async def get_live_metrics(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: LiveRoomService = Depends(lambda: live_room_service),
):
    """
    Get live metrics.
    - LIVE room: real-time from Redis (current viewers, peak, total joins)
    - ENDED room: historic from PostgreSQL live_sessions record
    """
    return await service.get_metrics(db, room_id)


@router.post("/{room_id}/reconcile")
async def reconcile_live_viewers(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
    service: LiveRoomService = Depends(lambda: live_room_service),
):
    """Admin: reconcile Redis viewer set against LiveKit participant list."""
    return await service.reconcile_viewers(db, room_id)


@router.post("/webhooks/livekit")
async def livekit_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
    service: LiveRoomService = Depends(lambda: live_room_service),
):
    """
    LiveKit webhook receiver — no JWT auth (LiveKit signs via Authorization header).
    Processes: participant_joined, participant_left, room_finished.
    """
    body = await request.body()
    return await service.handle_livekit_webhook(
        db, body=body, authorization=authorization or ""
    )
