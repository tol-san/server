import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
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
    """Service handling rule-based recommendation algorithms and Redis caching."""

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
        cache_key = f"cache:rec:comm:{current_user.id}:{limit}:{offset}"
        cached = await cache_service.get(cache_key)
        if cached:
            return PaginatedRecommendedCommunitiesResponse.model_validate(cached)

        raw_items, total = await self.repo.recommend_communities(
            db, user_id=current_user.id, limit=limit, offset=offset
        )
        items = [RecommendedCommunityResponse(**item) for item in raw_items]
        resp = PaginatedRecommendedCommunitiesResponse(
            items=items, total=total, limit=limit, offset=offset
        )

        await cache_service.set(cache_key, resp.model_dump(mode="json"), ttl=600)
        return resp

    async def recommend_users(
        self,
        db: AsyncSession,
        current_user: User,
        limit: int = 10,
        offset: int = 0,
    ) -> PaginatedRecommendedUsersResponse:
        cache_key = f"cache:rec:users:{current_user.id}:{limit}:{offset}"
        cached = await cache_service.get(cache_key)
        if cached:
            return PaginatedRecommendedUsersResponse.model_validate(cached)

        raw_items, total = await self.repo.recommend_users(
            db, user_id=current_user.id, limit=limit, offset=offset
        )
        items = [RecommendedUserResponse(**item) for item in raw_items]
        resp = PaginatedRecommendedUsersResponse(
            items=items, total=total, limit=limit, offset=offset
        )

        await cache_service.set(cache_key, resp.model_dump(mode="json"), ttl=600)
        return resp

    async def invalidate_user_recommendations(self, user_id: uuid.UUID) -> None:
        """Invalidate recommendations for a user when their interests or follows change."""
        await cache_service.delete_pattern(f"cache:rec:*:{user_id}:*")


recommendation_service = RecommendationService()

