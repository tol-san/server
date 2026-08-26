from sqlalchemy.ext.asyncio import AsyncSession

from app.recommendations.repository import (
    RecommendationRepository,
    recommendation_repository,
)
from app.recommendations.schemas import (
    PaginatedRecommendedCommunitiesResponse,
    PaginatedRecommendedUsersResponse,
    RecommendedCommunityResponse,
    RecommendedUserResponse,
)
from app.users.models import User


class RecommendationService:
    """Service handling rule-based recommendation algorithms for communities and users."""

    def __init__(
        self, repo: RecommendationRepository = recommendation_repository
    ):
        self.repo = repo

    async def recommend_communities(
        self,
        db: AsyncSession,
        current_user: User,
        limit: int = 10,
        offset: int = 0,
    ) -> PaginatedRecommendedCommunitiesResponse:
        raw_items, total = await self.repo.recommend_communities(
            db, user_id=current_user.id, limit=limit, offset=offset
        )
        items = [RecommendedCommunityResponse(**item) for item in raw_items]
        return PaginatedRecommendedCommunitiesResponse(
            items=items, total=total, limit=limit, offset=offset
        )

    async def recommend_users(
        self,
        db: AsyncSession,
        current_user: User,
        limit: int = 10,
        offset: int = 0,
    ) -> PaginatedRecommendedUsersResponse:
        raw_items, total = await self.repo.recommend_users(
            db, user_id=current_user.id, limit=limit, offset=offset
        )
        items = [RecommendedUserResponse(**item) for item in raw_items]
        return PaginatedRecommendedUsersResponse(
            items=items, total=total, limit=limit, offset=offset
        )


recommendation_service = RecommendationService()
