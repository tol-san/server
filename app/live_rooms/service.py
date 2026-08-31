"""
Live Streaming Room Service — control plane business logic.

Responsibilities:
  - Room lifecycle: create, start, end
  - LiveKit token generation (host/viewer)
  - Webhook handling (participant_joined/left, room_finished)
  - Viewer metric reconciliation via LiveKit RoomService
  - Transactional outbox events on key lifecycle transitions
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.communities.repository import CommunityRepository, community_repository
from app.core.config import settings
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.core.observability import LIVE_SESSIONS_TOTAL, LIVE_TOKENS_ISSUED
from app.core.outbox import publish as outbox_publish
from app.live_rooms.livekit import generate_livekit_token, list_participants
from app.live_rooms.models import LiveRoom
from app.live_rooms.repository import LiveRoomRepository, live_room_repository
from app.live_rooms.schemas import (
    LiveMetricsResponse,
    LiveRoomCreate,
    LiveRoomResponse,
    LiveRoomStatus,
    LiveRoomUpdate,
    LiveSessionResponse,
    LiveTokenResponse,
)
from app.live_rooms.viewer_tracker import ViewerTracker, viewer_tracker
from app.users.models import User

logger = logging.getLogger(__name__)


def _room_name(community_slug: str) -> str:
    """Generate a unique LiveKit room name."""
    return f"genz-{community_slug}-{uuid.uuid4().hex[:8]}"


def _map_room(room: LiveRoom, current_viewers: int = 0) -> LiveRoomResponse:
    return LiveRoomResponse(
        id=room.id,
        community_id=room.community_id,
        created_by=room.created_by,
        title=room.title,
        description=room.description,
        provider=room.provider,
        provider_room_name=room.provider_room_name,
        status=LiveRoomStatus(room.status),
        current_viewers=current_viewers,
        created_at=room.created_at,
        updated_at=room.updated_at,
    )


class LiveRoomService:
    def __init__(
        self,
        repo: LiveRoomRepository = live_room_repository,
        comm_repo: CommunityRepository = community_repository,
        tracker: ViewerTracker = viewer_tracker,
    ):
        self.repo = repo
        self.comm_repo = comm_repo
        self.tracker = tracker

    async def _require_member(
        self, db: AsyncSession, community_id: uuid.UUID, current_user: User
    ):
        if current_user.is_superuser:
            return None
        member = await self.comm_repo.get_membership(
            db, community_id=community_id, user_id=current_user.id
        )
        if not member:
            raise ForbiddenException("You must be a community member to access this live room.")
        return member

    async def _require_host_role(
        self, db: AsyncSession, community_id: uuid.UUID, current_user: User
    ) -> None:
        if current_user.is_superuser:
            return
        member = await self._require_member(db, community_id, current_user)
        if member.role not in ("owner", "moderator"):
            raise ForbiddenException("Only community owners/moderators can manage live rooms.")

    # ─────────────────────────────────────────────────────────────────────────
    # Room CRUD
    # ─────────────────────────────────────────────────────────────────────────

    async def create_room(
        self,
        db: AsyncSession,
        *,
        community_id: uuid.UUID,
        current_user: User,
        payload: LiveRoomCreate,
    ) -> LiveRoomResponse:
        # Only community owner or moderator can create
        member = await self.comm_repo.get_membership(
            db, community_id=community_id, user_id=current_user.id
        )
        if not member or member.role not in ("owner", "moderator"):
            raise ForbiddenException("Only community owners/moderators can create live rooms.")

        community = await self.comm_repo.get_by_id(db, community_id=community_id)
        if not community:
            raise NotFoundException("Community not found.")

        slug = community.slug if hasattr(community, "slug") else str(community_id)[:8]
        provider_room_name = f"genz-{slug}-{uuid.uuid4().hex[:8]}"

        async with db.begin_nested():
            room = await self.repo.create(
                db,
                community_id=community_id,
                created_by=current_user.id,
                title=payload.title,
                description=payload.description,
                provider="LIVEKIT",
                provider_room_name=provider_room_name,
            )
            await outbox_publish(
                db,
                event_type="live_room.created",
                aggregate_type="live_room",
                aggregate_id=str(room.id),
                payload={
                    "room_id": str(room.id),
                    "community_id": str(community_id),
                    "host_id": str(current_user.id),
                    "title": payload.title,
                },
            )

        await db.commit()

        return _map_room(room)

    async def get_room(
        self,
        db: AsyncSession,
        room_id: uuid.UUID,
        current_user: User,
    ) -> LiveRoomResponse:
        room = await self.repo.get_by_id(db, room_id)
        if not room:
            raise NotFoundException("Live room not found.")
        await self._require_member(db, room.community_id, current_user)
        # Get current viewer count from Redis if LIVE
        current_viewers = 0
        if room.status == LiveRoom.Status.LIVE:
            session = await self.repo.get_active_session(db, room_id)
            if session:
                current_viewers = await self.tracker.get_current_viewers(str(session.id))
        return _map_room(room, current_viewers)

    async def update_room(
        self,
        db: AsyncSession,
        room_id: uuid.UUID,
        current_user: User,
        payload: LiveRoomUpdate,
    ) -> LiveRoomResponse:
        room = await self.repo.get_by_id(db, room_id)
        if not room:
            raise NotFoundException("Live room not found.")
        await self._require_host_role(db, room.community_id, current_user)
        updates = payload.model_dump(exclude_unset=True)
        if updates:
            room = await self.repo.update(db, room_id, **updates)
            await db.commit()
        return _map_room(room)

    # ─────────────────────────────────────────────────────────────────────────
    # Session Lifecycle
    # ─────────────────────────────────────────────────────────────────────────

    async def start_session(
        self,
        db: AsyncSession,
        room_id: uuid.UUID,
        current_user: User,
    ) -> LiveTokenResponse:
        room = await self.repo.get_by_id_for_update(db, room_id)
        if not room:
            raise NotFoundException("Live room not found.")
        await self._require_host_role(db, room.community_id, current_user)
        if room.status == LiveRoom.Status.LIVE:
            raise BadRequestException("A session is already live for this room.")
        if room.status == LiveRoom.Status.ENDED:
            raise BadRequestException("This room has already ended. Create a new room.")

        async with db.begin_nested():
            await self.repo.update_status(db, room_id, LiveRoom.Status.LIVE)
            session = await self.repo.create_session(
                db, room_id=room_id, host_id=current_user.id
            )
            await outbox_publish(
                db,
                event_type="live_room.session_started",
                aggregate_type="live_session",
                aggregate_id=str(session.id),
                payload={
                    "room_id": str(room_id),
                    "session_id": str(session.id),
                    "community_id": str(room.community_id),
                    "host_id": str(current_user.id),
                    "started_at": session.started_at.isoformat(),
                },
            )

        await db.commit()

        profile = getattr(current_user, "profile", None)
        username = (profile.display_name if profile and profile.display_name else current_user.username)

        token = generate_livekit_token(
            room_name=room.provider_room_name,
            user_id=str(current_user.id),
            username=username,
            is_host=True,
        )

        LIVE_SESSIONS_TOTAL.labels(community_id=str(room.community_id)).inc()
        LIVE_TOKENS_ISSUED.labels(role="host").inc()

        return LiveTokenResponse(
            token=token,
            livekit_url=settings.LIVEKIT_URL,
            room_name=room.provider_room_name,
            participant_identity=str(current_user.id),
            is_host=True,
            session_id=session.id,
        )

    async def request_viewer_token(
        self,
        db: AsyncSession,
        room_id: uuid.UUID,
        current_user: User,
    ) -> LiveTokenResponse:
        room = await self.repo.get_by_id(db, room_id)
        if not room:
            raise NotFoundException("Live room not found.")
        if room.status != LiveRoom.Status.LIVE:
            raise BadRequestException("This room is not currently live.")

        # Verify community membership
        member = await self.comm_repo.get_membership(
            db, community_id=room.community_id, user_id=current_user.id
        )
        if not member:
            raise ForbiddenException("You must be a community member to join this live room.")

        # Get active session ID for response
        session = await self.repo.get_active_session(db, room_id)

        profile = getattr(current_user, "profile", None)
        username = (profile.display_name if profile and profile.display_name else current_user.username)

        # Generate viewer token — viewer count incremented ONLY via webhook
        token = generate_livekit_token(
            room_name=room.provider_room_name,
            user_id=str(current_user.id),
            username=username,
            is_host=False,
        )

        LIVE_TOKENS_ISSUED.labels(role="viewer").inc()

        return LiveTokenResponse(
            token=token,
            livekit_url=settings.LIVEKIT_URL,
            room_name=room.provider_room_name,
            participant_identity=str(current_user.id),
            is_host=False,
            session_id=session.id if session else None,
        )

    async def end_session(
        self,
        db: AsyncSession,
        room_id: uuid.UUID,
        current_user: User,
    ) -> LiveSessionResponse:
        room = await self.repo.get_by_id_for_update(db, room_id)
        if not room:
            raise NotFoundException("Live room not found.")
        await self._require_host_role(db, room.community_id, current_user)
        if room.status != LiveRoom.Status.LIVE:
            raise BadRequestException("Room is not currently live.")

        session = await self.repo.get_active_session(db, room_id)
        if not session:
            raise BadRequestException("No active session found for this room.")

        session_id_str = str(session.id)
        now = datetime.now(timezone.utc)
        duration = int((now - session.started_at).total_seconds())

        # Fetch final metrics from Redis before cleanup
        peak = await self.tracker.get_peak_viewers(session_id_str)
        unique = await self.tracker.get_unique_viewers(session_id_str)
        total_joins = await self.tracker.get_total_joins(session_id_str)

        async with db.begin_nested():
            closed = await self.repo.close_session(
                db,
                session.id,
                ended_at=now,
                duration_seconds=duration,
                peak_viewers=peak,
                unique_viewers=unique,
                total_joins=total_joins,
            )
            await self.repo.update_status(db, room_id, LiveRoom.Status.ENDED)
            await outbox_publish(
                db,
                event_type="live_room.session_ended",
                aggregate_type="live_session",
                aggregate_id=session_id_str,
                payload={
                    "room_id": str(room_id),
                    "session_id": session_id_str,
                    "community_id": str(room.community_id),
                    "host_id": str(current_user.id),
                    "duration_seconds": duration,
                    "peak_viewers": peak,
                    "unique_viewers": unique,
                    "total_joins": total_joins,
                },
            )

        await db.commit()
        await self.tracker.cleanup(session_id_str)

        return LiveSessionResponse.model_validate(closed)

    # ─────────────────────────────────────────────────────────────────────────
    # Metrics
    # ─────────────────────────────────────────────────────────────────────────

    async def get_metrics(
        self, db: AsyncSession, room_id: uuid.UUID, current_user: User
    ) -> LiveMetricsResponse:
        room = await self.repo.get_by_id(db, room_id)
        if not room:
            raise NotFoundException("Live room not found.")
        await self._require_member(db, room.community_id, current_user)

        session = await self.repo.get_active_session(db, room_id)

        if room.status == LiveRoom.Status.LIVE and session:
            sid = str(session.id)
            current = await self.tracker.get_current_viewers(sid)
            peak = await self.tracker.get_peak_viewers(sid)
            unique = await self.tracker.get_unique_viewers(sid)
            total_joins = await self.tracker.get_total_joins(sid)
            duration = int((datetime.now(timezone.utc) - session.started_at).total_seconds())
            started_at = session.started_at
            session_id = session.id
        elif session and session.ended_at:
            current = 0
            peak = session.peak_viewers
            unique = session.unique_viewers
            total_joins = session.total_joins
            duration = session.duration_seconds
            started_at = session.started_at
            session_id = session.id
        else:
            current = peak = unique = total_joins = duration = 0
            started_at = None
            session_id = None

        return LiveMetricsResponse(
            room_id=room_id,
            session_id=session_id,
            status=LiveRoomStatus(room.status),
            current_viewers=current,
            peak_viewers=peak,
            unique_viewers=unique,
            total_joins=total_joins,
            started_at=started_at,
            duration_seconds=duration,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Webhook handler
    # ─────────────────────────────────────────────────────────────────────────

    async def handle_livekit_webhook(
        self,
        db: AsyncSession,
        body: bytes,
        authorization: str,
    ) -> dict:
        """
        Process a LiveKit webhook event with signature verification and idempotency.
        Correct viewer count: only participant_joined/left webhooks update Redis.
        """
        import hashlib

        # Verify LiveKit JWT signature
        try:
            from livekit.api import WebhookReceiver
            receiver = WebhookReceiver(
                settings.LIVEKIT_API_KEY,
                settings.LIVEKIT_API_SECRET,
            )
            event = receiver.receive(body, authorization)
        except Exception as exc:
            logger.warning("LiveKit webhook signature verification failed: %s", exc)
            raise BadRequestException("Invalid webhook signature.")

        event_id = getattr(event, "id", None) or hashlib.sha256(body).hexdigest()
        raw_event_type = getattr(event, "event", None) or event.__class__.__name__
        event_type = {
            "participant_joined": "ParticipantJoined",
            "participant_left": "ParticipantLeft",
            "room_finished": "RoomFinished",
        }.get(str(raw_event_type), str(raw_event_type))

        # Idempotency check
        is_new = await self.repo.try_store_provider_event(
            db,
            provider="LIVEKIT",
            provider_event_id=str(event_id),
            event_type=event_type,
        )
        if not is_new:
            return {"status": "duplicate", "event_type": event_type}

        await db.commit()

        # Route by event type
        await self._route_webhook_event(db, event, event_type)
        await self.repo.mark_provider_event_processed(
            db, provider="LIVEKIT", provider_event_id=str(event_id)
        )
        await db.commit()

        return {"status": "processed", "event_type": event_type}

    async def _route_webhook_event(self, db: AsyncSession, event, event_type: str) -> None:
        """Route processed webhook to the appropriate handler."""
        if event_type == "ParticipantJoined":
            room_name = event.room.name if hasattr(event, "room") else None
            participant_identity = (
                event.participant.identity if hasattr(event, "participant") else None
            )
            if room_name and participant_identity:
                room = await self.repo.get_by_provider_room_name(db, room_name)
                if room:
                    session = await self.repo.get_active_session(db, room.id)
                    if session:
                        await self.tracker.participant_joined(
                            str(session.id), participant_identity
                        )

        elif event_type == "ParticipantLeft":
            room_name = event.room.name if hasattr(event, "room") else None
            participant_identity = (
                event.participant.identity if hasattr(event, "participant") else None
            )
            if room_name and participant_identity:
                room = await self.repo.get_by_provider_room_name(db, room_name)
                if room:
                    session = await self.repo.get_active_session(db, room.id)
                    if session:
                        await self.tracker.participant_left(
                            str(session.id), participant_identity
                        )

        elif event_type == "RoomFinished":
            room_name = event.room.name if hasattr(event, "room") else None
            if room_name:
                room = await self.repo.get_by_provider_room_name(db, room_name)
                if room and room.status == LiveRoom.Status.LIVE:
                    session = await self.repo.get_active_session(db, room.id)
                    if session:
                        sid = str(session.id)
                        now = datetime.now(timezone.utc)
                        duration = int((now - session.started_at).total_seconds())
                        peak = await self.tracker.get_peak_viewers(sid)
                        unique = await self.tracker.get_unique_viewers(sid)
                        total_joins = await self.tracker.get_total_joins(sid)
                        await self.repo.close_session(
                            db,
                            session.id,
                            ended_at=now,
                            duration_seconds=duration,
                            peak_viewers=peak,
                            unique_viewers=unique,
                            total_joins=total_joins,
                        )
                        await self.repo.update_status(
                            db, room.id, LiveRoom.Status.ENDED
                        )
                        await db.commit()
                        await self.tracker.cleanup(sid)

    # ─────────────────────────────────────────────────────────────────────────
    # Reconciliation
    # ─────────────────────────────────────────────────────────────────────────

    async def reconcile_viewers(
        self, db: AsyncSession, room_id: uuid.UUID
    ) -> dict:
        """
        Compare Redis participant set against LiveKit RoomService.
        Sync any discrepancies (handles missed webhooks).
        """
        room = await self.repo.get_by_id(db, room_id)
        if not room or room.status != LiveRoom.Status.LIVE:
            return {"status": "not_live"}

        session = await self.repo.get_active_session(db, room_id)
        if not session:
            return {"status": "no_active_session"}

        lk_participants = await list_participants(room.provider_room_name)
        lk_identities = {p["identity"] for p in lk_participants}

        redis_identities = await self.tracker.get_participant_ids(str(session.id))

        # Add missing
        for identity in lk_identities - redis_identities:
            await self.tracker.participant_joined(str(session.id), identity)

        # Remove stale
        for identity in redis_identities - lk_identities:
            await self.tracker.participant_left(str(session.id), identity)

        return {
            "status": "reconciled",
            "livekit_count": len(lk_identities),
            "redis_before": len(redis_identities),
            "redis_after": await self.tracker.get_current_viewers(str(session.id)),
        }


live_room_service = LiveRoomService()
