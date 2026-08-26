from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_superuser
from app.core.database import get_db
from app.interests.schemas import InterestCreateRequest, InterestResponse
from app.interests.service import InterestService, interest_service
from app.users.models import User

router = APIRouter(prefix="/interests", tags=["Interests"])


@router.get(
    "",
    response_model=List[InterestResponse],
    status_code=status.HTTP_200_OK,
    summary="List all interest categories",
    description="Retrieve the master catalog of predefined interest categories.",
)
async def list_interests(
    db: AsyncSession = Depends(get_db),
    service: InterestService = Depends(lambda: interest_service),
) -> List[InterestResponse]:
    return await service.list_interests(db)


@router.post(
    "",
    response_model=InterestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create interest category",
    description="Create a new interest category in the catalog (System Administrator only).",
)
async def create_interest(
    payload: InterestCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_superuser),
    service: InterestService = Depends(lambda: interest_service),
) -> InterestResponse:
    return await service.create_interest(db, payload)
