import re
import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.interests.models import Interest
from app.interests.repository import InterestRepository, interest_repository
from app.interests.schemas import (
    InterestCreateRequest,
    InterestResponse,
    UserInterestsResponse,
    UserInterestsUpdateRequest,
)


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text).strip("-")


class InterestService:
    """Service handling interests taxonomy and user interests assignment."""

    def __init__(self, interest_repo: InterestRepository = interest_repository):
        self.interest_repo = interest_repo

    async def list_interests(self, db: AsyncSession) -> List[InterestResponse]:
        interests = await self.interest_repo.get_all(db)
        return [InterestResponse.model_validate(i) for i in interests]

    async def create_interest(
        self,
        db: AsyncSession,
        payload: InterestCreateRequest,
    ) -> InterestResponse:
        # Check name uniqueness
        existing_name = await self.interest_repo.get_by_name(db, payload.name)
        if existing_name:
            raise BadRequestException(f"Interest category '{payload.name}' already exists.")

        # Generate slug if omitted
        slug = payload.slug.strip() if payload.slug else slugify(payload.name)

        # Check slug uniqueness
        existing_slug = await self.interest_repo.get_by_slug(db, slug)
        if existing_slug:
            raise BadRequestException(f"Interest with slug '{slug}' already exists.")

        interest = await self.interest_repo.create(
            db,
            name=payload.name,
            slug=slug,
            icon_url=payload.icon_url,
            description=payload.description,
        )

        from app.core.meilisearch import meilisearch_service
        await meilisearch_service.index_interest(
            {
                "id": str(interest.id),
                "name": interest.name,
                "slug": interest.slug,
                "description": interest.description,
                "icon_url": interest.icon_url,
                "created_at": interest.created_at.isoformat() if interest.created_at else None,
            }
        )

        return InterestResponse.model_validate(interest)

    async def get_user_interests(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> UserInterestsResponse:
        interests = await self.interest_repo.get_user_interests(db, user_id)
        items = [InterestResponse.model_validate(i) for i in interests]
        return UserInterestsResponse(items=items, total=len(items))

    async def update_user_interests(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        payload: UserInterestsUpdateRequest,
    ) -> UserInterestsResponse:
        unique_ids = list(dict.fromkeys(payload.interest_ids))

        # Validate that all requested interest IDs exist
        if unique_ids:
            found_interests = await self.interest_repo.get_by_ids(db, unique_ids)
            if len(found_interests) != len(unique_ids):
                found_ids = {i.id for i in found_interests}
                missing = [str(uid) for uid in unique_ids if uid not in found_ids]
                raise BadRequestException(f"Invalid interest ID(s) provided: {', '.join(missing)}")

        updated_interests = await self.interest_repo.set_user_interests(db, user_id, unique_ids)

        # Invalidate recommendation & shorts cache for this user
        from app.feeds.service import feed_service
        from app.recommendations.service import recommendation_service
        await recommendation_service.invalidate_user_recommendations(user_id)
        await feed_service.invalidate_user_feeds(user_id)

        items = [InterestResponse.model_validate(i) for i in updated_interests]
        return UserInterestsResponse(items=items, total=len(items))


interest_service = InterestService()
