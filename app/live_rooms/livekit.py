"""
LiveKit integration layer — token generation and RoomService reconciliation.

Token scopes:
  Host    → can_publish=True,  can_subscribe=True,  can_publish_data=False
  Viewer  → can_publish=False, can_subscribe=True,  can_publish_data=False

Notes:
  - .with_ttl() requires a datetime.timedelta (not an int)
  - can_publish_data is intentionally False — live comments go through FastAPI WS
"""
from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, List

from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_livekit_token(
    *,
    room_name: str,
    user_id: str,
    username: str,
    is_host: bool,
    api_key: str = "",
    api_secret: str = "",
    ttl_hours: int = 1,
) -> str:
    """Generate a scoped LiveKit JWT for host or viewer participation."""
    from livekit import api as lk_api

    key = api_key or settings.LIVEKIT_API_KEY
    secret = api_secret or settings.LIVEKIT_API_SECRET

    grants = lk_api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=is_host,
        can_subscribe=True,
        can_publish_data=False,  # app-level chat handles text
    )

    token = (
        lk_api.AccessToken(key, secret)
        .with_identity(user_id)
        .with_name(username)
        .with_grants(grants)
        .with_ttl(datetime.timedelta(hours=ttl_hours))
        .to_jwt()
    )
    return token


async def list_participants(room_name: str) -> List[Dict[str, Any]]:
    """
    Reconciliation: fetch live participant list from LiveKit RoomService.
    Returns a list of participant identity strings currently in the room.
    """
    try:
        from livekit import api as lk_api

        room_service = lk_api.RoomService(
            settings.LIVEKIT_URL,
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_API_SECRET,
        )
        participants = await room_service.list_participants(room=room_name)
        return [
            {"identity": p.identity, "name": p.name}
            for p in (participants.participants if hasattr(participants, "participants") else [])
        ]
    except Exception as exc:
        logger.warning("LiveKit list_participants failed for room %s: %s", room_name, exc)
        return []
