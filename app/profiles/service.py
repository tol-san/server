from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import storage_service
from app.profiles.schemas import CurrentUserProfileResponse, ProfileUpdateRequest
from app.users.models import User
from app.users.repository import UserRepository, user_repository


class ProfileService:
    """Service handling profile inspection and editing."""

    def __init__(self, user_repo: UserRepository = user_repository):
        self.user_repo = user_repo

    async def get_current_profile(
        self,
        db: AsyncSession,
        current_user: User,
    ) -> CurrentUserProfileResponse:
        profile = current_user.profile
        return CurrentUserProfileResponse(
            id=current_user.id,
            email=current_user.email,
            username=current_user.username,
            is_active=current_user.is_active,
            display_name=profile.display_name if profile and profile.display_name else current_user.username,
            bio=profile.bio if profile else None,
            avatar_url=profile.avatar_url if profile else None,
            follower_count=profile.follower_count if profile else 0,
            following_count=profile.following_count if profile else 0,
            post_count=profile.post_count if profile else 0,
            created_at=current_user.created_at,
            updated_at=profile.updated_at if profile else current_user.updated_at,
        )

    async def update_current_profile(
        self,
        db: AsyncSession,
        current_user: User,
        payload: ProfileUpdateRequest,
    ) -> CurrentUserProfileResponse:
        updates = payload.model_dump(exclude_unset=True)
        profile = await self.user_repo.update_profile(
            db,
            current_user,
            **updates,
        )

        return CurrentUserProfileResponse(
            id=current_user.id,
            email=current_user.email,
            username=current_user.username,
            is_active=current_user.is_active,
            display_name=profile.display_name if profile and profile.display_name else current_user.username,
            bio=profile.bio if profile else None,
            avatar_url=profile.avatar_url if profile else None,
            follower_count=profile.follower_count if profile else 0,
            following_count=profile.following_count if profile else 0,
            post_count=profile.post_count if profile else 0,
            created_at=current_user.created_at,
            updated_at=profile.updated_at if profile else current_user.updated_at,
        )

    async def upload_avatar(
        self,
        db: AsyncSession,
        current_user: User,
        file: UploadFile,
    ) -> CurrentUserProfileResponse:
        avatar_url = await storage_service.upload_avatar(current_user.id, file)
        profile = await self.user_repo.update_profile(
            db,
            current_user,
            avatar_url=avatar_url,
        )

        return CurrentUserProfileResponse(
            id=current_user.id,
            email=current_user.email,
            username=current_user.username,
            is_active=current_user.is_active,
            display_name=profile.display_name if profile and profile.display_name else current_user.username,
            bio=profile.bio if profile else None,
            avatar_url=profile.avatar_url,
            follower_count=profile.follower_count if profile else 0,
            following_count=profile.following_count if profile else 0,
            post_count=profile.post_count if profile else 0,
            created_at=current_user.created_at,
            updated_at=profile.updated_at if profile else current_user.updated_at,
        )


profile_service = ProfileService()
