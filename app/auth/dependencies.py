import uuid
from typing import Optional
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

    if payload.get("ver") != user.token_version:
        raise UnauthorizedException("Session has been revoked.")

    if not user.is_active:
        raise ForbiddenException("User account is inactive.")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency ensuring the user is active."""
    return current_user


async def get_current_jti(
    token: str = Depends(oauth2_scheme),
) -> Optional[str]:
    """Extract session JTI from current access token if present."""
    try:
        payload = decode_token(token)
        return payload.get("jti")
    except Exception:
        return None



async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency ensuring the user is a superuser."""
    if not current_user.is_superuser:
        raise ForbiddenException("Administrator privileges required.")
    return current_user


oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)


async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Return authenticated user if a valid token is provided, or None for anonymous callers."""
    if not token:
        return None
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise UnauthorizedException("Invalid token type. Expected access token.")
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException("Invalid token payload.")
    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise UnauthorizedException("Invalid user identifier in token.")
    user = await user_repository.get_by_id(db, user_id)
    if not user or payload.get("ver") != user.token_version:
        raise UnauthorizedException("Session has been revoked.")
    if not user.is_active:
        raise ForbiddenException("User account is inactive.")
    return user
