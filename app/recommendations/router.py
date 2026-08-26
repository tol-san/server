from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.recommendations.schemas import (
    PaginatedRecommendedCommunitiesResponse,
    PaginatedRecommendedUsersResponse,
)
from app.recommendations.service import (
    RecommendationService,
    recommendation_service,
)
from app.users.models import User

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get(
    "/communities",
    response_model=PaginatedRecommendedCommunitiesResponse,
    status_code=status.HTTP_200_OK,
    summary="Recommend communities",
    description="Recommend communities based on user's selected interests, excluding already joined communities.",
)
async def recommend_communities(
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: RecommendationService = Depends(lambda: recommendation_service),
) -> PaginatedRecommendedCommunitiesResponse:
    return await service.recommend_communities(
        db, current_user=current_user, limit=limit, offset=offset
    )


@router.get(
    "/users",
    response_model=PaginatedRecommendedUsersResponse,
    status_code=status.HTTP_200_OK,
    summary="Recommend users by interest",
    description="Recommend other users who share overlapping interests, excluding already followed and blocked users.",
)
async def recommend_users(
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: RecommendationService = Depends(lambda: recommendation_service),
) -> PaginatedRecommendedUsersResponse:
    return await service.recommend_users(
        db, current_user=current_user, limit=limit, offset=offset
    )
