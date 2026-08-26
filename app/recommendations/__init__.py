"""Recommendations module providing community and user recommendation algorithms."""

from app.recommendations.repository import (
    RecommendationRepository,
    recommendation_repository,
)
from app.recommendations.router import router as recommendations_router
from app.recommendations.schemas import (
    PaginatedRecommendedCommunitiesResponse,
    PaginatedRecommendedUsersResponse,
    RecommendedCommunityResponse,
    RecommendedUserResponse,
)
from app.recommendations.service import (
    RecommendationService,
    recommendation_service,
)

__all__ = [
    "RecommendationRepository",
    "recommendation_repository",
    "RecommendationService",
    "recommendation_service",
    "recommendations_router",
    "RecommendedCommunityResponse",
    "PaginatedRecommendedCommunitiesResponse",
    "RecommendedUserResponse",
    "PaginatedRecommendedUsersResponse",
]
