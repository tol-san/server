import uuid
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.users.models import User
from app.users.repository import user_repository

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=True,
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate access token and return the authenticated user."""
    payload = decode_token(token)

    token_type = payload.get("type")
    if token_type != "access":
        raise UnauthorizedException("Invalid token type. Expected access token.")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException("Invalid token payload.")

    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise UnauthorizedException("Invalid user identifier in token.")

    user = await user_repository.get_by_id(db, user_id)
    if not user:
        raise UnauthorizedException("User not found.")

    if not user.is_active:
        raise ForbiddenException("User account is inactive.")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency ensuring the user is active."""
    return current_user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency ensuring the user is a superuser."""
    if not current_user.is_superuser:
        raise ForbiddenException("Administrator privileges required.")
    return current_user
