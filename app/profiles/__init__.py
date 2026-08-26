"""Profiles module containing profile schemas, services, and routers."""

from app.profiles.router import router as profiles_router
from app.profiles.schemas import CurrentUserProfileResponse, ProfileUpdateRequest
from app.profiles.service import ProfileService, profile_service

__all__ = [
    "profiles_router",
    "ProfileUpdateRequest",
    "CurrentUserProfileResponse",
    "ProfileService",
    "profile_service",
]
