import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class UserPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    follower_count: int = 0
    following_count: int = 0
    post_count: int = 0
    created_at: datetime


class UserItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    follower_count: int = 0
    following_count: int = 0


class PaginatedUsersResponse(BaseModel):
    items: List[UserItemResponse]
    total: int
    limit: int
    offset: int


class RelationshipResponse(BaseModel):
    is_following: bool
    is_followed_by: bool
    is_blocking: bool
    is_blocked_by: bool


class FollowActionResponse(BaseModel):
    is_following: bool
    message: str


class BlockActionResponse(BaseModel):
    is_blocking: bool
    message: str


class UserPrivacyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_private: bool = False
    allow_comments: str = "everyone"
    allow_mentions: str = "everyone"
    show_activity_status: bool = True
    search_discoverable: bool = True


class UserPrivacyUpdateRequest(BaseModel):
    is_private: Optional[bool] = None
    allow_comments: Optional[str] = None
    allow_mentions: Optional[str] = None
    show_activity_status: Optional[bool] = None
    search_discoverable: Optional[bool] = None


class DeactivateAccountRequest(BaseModel):
    password: str
    reason: Optional[str] = None


class DeleteAccountRequest(BaseModel):
    password: str
    confirmation: str

