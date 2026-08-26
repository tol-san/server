from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.users.schemas import UserPublicResponse
from app.users.service import UserService, user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/{username}",
    response_model=UserPublicResponse,
    status_code=status.HTTP_200_OK,
    summary="Get public user profile",
    description="Retrieve public profile and stats for a given username.",
)
async def get_user_profile(
    username: str,
    db: AsyncSession = Depends(get_db),
    service: UserService = Depends(lambda: user_service),
) -> UserPublicResponse:
    return await service.get_public_profile(db, username)
