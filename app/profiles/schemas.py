import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProfileUpdateRequest(BaseModel):
    username: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=30,
        pattern=r"^[a-z0-9_-]+$",
        description="Unique username (3-30 lowercase letters, numbers, underscores, hyphens)",
    )
    display_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Profile display name (1-100 characters)",
    )
    bio: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Profile bio description (maximum 500 characters)",
    )
    avatar_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Avatar image URL",
    )


class CurrentUserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str
    is_active: bool
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    follower_count: int = 0
    following_count: int = 0
    post_count: int = 0
    created_at: datetime
    updated_at: datetime
