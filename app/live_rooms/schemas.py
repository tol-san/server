"""Pydantic v2 schemas for live streaming rooms."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class LiveRoomStatus(str, Enum):
    READY = "READY"
    LIVE = "LIVE"
    ENDED = "ENDED"
    CANCELLED = "CANCELLED"


class LiveRoomProvider(str, Enum):
    LIVEKIT = "LIVEKIT"


# ─────────────────────────────────────────────────────────────────────────────
# Request schemas
# ─────────────────────────────────────────────────────────────────────────────

class LiveRoomCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class LiveRoomUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


# ─────────────────────────────────────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class LiveRoomResponse(BaseModel):
    id: uuid.UUID
    community_id: uuid.UUID
    created_by: uuid.UUID
    title: str
    description: Optional[str]
    provider: str
    provider_room_name: str
    status: LiveRoomStatus
    current_viewers: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LiveSessionResponse(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    host_id: uuid.UUID
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: int
    peak_viewers: int
    unique_viewers: int
    total_joins: int

    model_config = {"from_attributes": True}


class LiveTokenResponse(BaseModel):
    """LiveKit token + connection details returned to host or viewer."""
    token: str
    livekit_url: str
    room_name: str
    participant_identity: str
    is_host: bool
    session_id: Optional[uuid.UUID] = None


class LiveMetricsResponse(BaseModel):
    room_id: uuid.UUID
    session_id: Optional[uuid.UUID]
    status: LiveRoomStatus
    current_viewers: int
    peak_viewers: int
    unique_viewers: int
    total_joins: int
    started_at: Optional[datetime]
    duration_seconds: int
