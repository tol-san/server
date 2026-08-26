import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Valid email address")
    username: str = Field(
        ...,
        min_length=3,
        max_length=30,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Username must be 3-30 characters (alphanumeric, underscores, hyphens only)",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password must be between 8 and 100 characters",
    )
    display_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional display name (defaults to username if not provided)",
    )


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    follower_count: int = 0
    following_count: int = 0
    post_count: int = 0
    created_at: datetime
    updated_at: datetime


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str
    is_active: bool
    created_at: datetime
    profile: Optional[ProfileResponse] = None
