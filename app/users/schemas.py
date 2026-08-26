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
