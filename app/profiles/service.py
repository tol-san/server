from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UsernameAlreadyExistsException
from app.core.storage import storage_service
from app.profiles.schemas import CurrentUserProfileResponse, ProfileUpdateRequest
from app.users.models import User
from app.users.repository import UserRepository, user_repository


class ProfileService:
    """Service handling profile inspection, editing, and avatar asset management."""

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

        if "username" in updates and updates["username"]:
            new_username = updates.pop("username").lower().strip()
            if new_username != current_user.username.lower():
                existing = await self.user_repo.get_by_username(db, new_username)
                if existing and existing.id != current_user.id:
                    raise UsernameAlreadyExistsException("This username is already taken.")
                current_user.username = new_username
                db.add(current_user)

        profile = await self.user_repo.update_profile(
            db,
            current_user,
            **updates,
        )

        # Update Meilisearch index
        from app.core.meilisearch import meilisearch_service
        await meilisearch_service.index_user(
            {
                "id": str(current_user.id),
                "username": current_user.username,
                "display_name": profile.display_name if profile and profile.display_name else current_user.username,
                "avatar_url": profile.avatar_url if profile else None,
                "bio": profile.bio if profile else None,
                "follower_count": profile.follower_count if profile else 0,
                "is_active": current_user.is_active,
                "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            }
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
        old_avatar_url = current_user.profile.avatar_url if current_user.profile else None
        avatar_url = await storage_service.upload_avatar(
            user_id=current_user.id,
            file=file,
            old_avatar_url=old_avatar_url,
        )
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

    async def delete_avatar(
        self,
        db: AsyncSession,
        current_user: User,
    ) -> CurrentUserProfileResponse:
        old_avatar_url = current_user.profile.avatar_url if current_user.profile else None
        if old_avatar_url:
            storage_service.delete_file_by_url(old_avatar_url)

        profile = await self.user_repo.update_profile(
            db,
            current_user,
            avatar_url="",
        )
        # Ensure avatar_url is explicitly None
        profile.avatar_url = None
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

        return CurrentUserProfileResponse(
            id=current_user.id,
            email=current_user.email,
            username=current_user.username,
            is_active=current_user.is_active,
            display_name=profile.display_name if profile and profile.display_name else current_user.username,
            bio=profile.bio if profile else None,
            avatar_url=None,
            follower_count=profile.follower_count if profile else 0,
            following_count=profile.following_count if profile else 0,
            post_count=profile.post_count if profile else 0,
            created_at=current_user.created_at,
            updated_at=profile.updated_at if profile else current_user.updated_at,
        )


profile_service = ProfileService()
