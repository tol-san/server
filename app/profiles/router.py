from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.profiles.schemas import CurrentUserProfileResponse, ProfileUpdateRequest
from app.profiles.service import ProfileService, profile_service
from app.users.models import User

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.get(
    "/me",
    response_model=CurrentUserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Retrieve account and profile information for the authenticated user.",
)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: ProfileService = Depends(lambda: profile_service),
) -> CurrentUserProfileResponse:
    return await service.get_current_profile(db, current_user)


@router.patch(
    "/me",
    response_model=CurrentUserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
    description="Update display name, bio, and avatar URL for the authenticated user.",
)
async def update_my_profile(
    payload: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: ProfileService = Depends(lambda: profile_service),
) -> CurrentUserProfileResponse:
    return await service.update_current_profile(db, current_user, payload)


@router.post(
    "/me/avatar",
    response_model=CurrentUserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload user avatar image",
    description="Upload an avatar image (JPEG, PNG, WebP, GIF, max 5MB), converts to mobile-optimized WebP, stores in MinIO, and updates profile.",
)
async def upload_avatar(
    file: UploadFile = File(..., description="Avatar image file to upload"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: ProfileService = Depends(lambda: profile_service),
) -> CurrentUserProfileResponse:
    return await service.upload_avatar(db, current_user, file)


@router.delete(
    "/me/avatar",
    response_model=CurrentUserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete user avatar",
    description="Delete the current avatar image from MinIO and reset avatar_url to null.",
)
async def delete_avatar(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: ProfileService = Depends(lambda: profile_service),
) -> CurrentUserProfileResponse:
    return await service.delete_avatar(db, current_user)
