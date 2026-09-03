import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class NotificationActor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recipient_id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    actor: Optional[NotificationActor] = None
    notification_type: str
    title: str
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime


class PaginatedNotificationsResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int
    limit: int
    offset: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class TypingIndicatorPayload(BaseModel):
    channel: str = Field(..., min_length=36, max_length=36)
    is_typing: bool = True


class NotificationPreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    likes_enabled: bool = True
    comments_enabled: bool = True
    follows_enabled: bool = True
    mentions_enabled: bool = True
    community_enabled: bool = True
    email_enabled: bool = False
    push_enabled: bool = True
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


class NotificationPreferencesUpdateRequest(BaseModel):
    likes_enabled: Optional[bool] = None
    comments_enabled: Optional[bool] = None
    follows_enabled: Optional[bool] = None
    mentions_enabled: Optional[bool] = None
    community_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None

