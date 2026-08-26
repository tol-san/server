from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import UserRegisterRequest, UserResponse
from app.auth.service import AuthService, auth_service
from app.core.database import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user account with email, username, and password, and initializes a default user profile.",
)
async def register(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(lambda: auth_service),
) -> UserResponse:
    user = await service.register_user(db, payload)
    return UserResponse.model_validate(user)
