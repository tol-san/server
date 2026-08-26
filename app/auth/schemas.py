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
        pattern=r"^[a-z0-9_-]+$",
        description="Username must be 3-30 characters (lowercase letters, numbers, underscores, and hyphens only)",
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


class LoginRequest(BaseModel):
    identifier: str = Field(
        ...,
        min_length=1,
        description="User email address or username",
    )
    password: str = Field(
        ...,
        min_length=1,
        description="User password",
    )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Active JWT refresh token")


class TokenRefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered account email address")


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Password reset verification token")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password (8-100 characters)",
    )


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password (8-100 characters)",
    )


class MessageResponse(BaseModel):
    message: str
