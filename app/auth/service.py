import time
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    TokenRefreshResponse,
    TokenResponse,
    UserRegisterRequest,
    UserResponse,
)
from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    EmailAlreadyExistsException,
    ForbiddenException,
    UnauthorizedException,
    UsernameAlreadyExistsException,
)
from app.core.otp import (
    generate_otp,
    store_password_reset_otp,
    verify_password_reset_otp,
)
from app.core.redis import blacklist_token, is_token_blacklisted
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.users.models import User
from app.users.repository import UserRepository, user_repository


class AuthService:
    """Service handling all authentication, token management, and password workflows."""

    def __init__(self, user_repo: UserRepository = user_repository):
        self.user_repo = user_repo

    async def register_user(
        self,
        db: AsyncSession,
        payload: UserRegisterRequest,
    ) -> User:
        # Check if email is already taken
        existing_user_by_email = await self.user_repo.get_by_email(db, payload.email)
        if existing_user_by_email:
            raise EmailAlreadyExistsException("A user with this email already exists.")

        # Check if username is already taken
        existing_user_by_username = await self.user_repo.get_by_username(db, payload.username)
        if existing_user_by_username:
            raise UsernameAlreadyExistsException("A user with this username already exists.")

        # Hash password securely
        hashed_password = get_password_hash(payload.password)

        # Create user with profile
        user = await self.user_repo.create_user_with_profile(
            db,
            email=payload.email,
            username=payload.username,
            hashed_password=hashed_password,
            display_name=payload.display_name,
        )

        # Index user into Meilisearch
        from app.core.meilisearch import meilisearch_service
        await meilisearch_service.index_user(
            {
                "id": str(user.id),
                "username": user.username,
                "display_name": user.profile.display_name if user.profile else user.username,
                "avatar_url": user.profile.avatar_url if user.profile else None,
                "bio": user.profile.bio if user.profile else None,
                "follower_count": 0,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
        )

        return user

    async def login(
        self,
        db: AsyncSession,
        payload: LoginRequest,
    ) -> TokenResponse:
        user = await self.user_repo.get_by_email_or_username(db, payload.identifier)
        if not user:
            raise UnauthorizedException("Invalid email/username or password.")

        if not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedException("Invalid email/username or password.")

        if not user.is_active:
            raise ForbiddenException("User account is deactivated.")

        access_token = create_access_token(user.id)
        refresh_token, _ = create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user),
        )

    async def refresh_tokens(
        self,
        db: AsyncSession,
        refresh_token_str: str,
    ) -> TokenRefreshResponse:
        payload = decode_token(refresh_token_str)

        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type. Expected refresh token.")

        jti = payload.get("jti")
        if not jti or await is_token_blacklisted(jti):
            raise UnauthorizedException("Refresh token has been revoked or is invalid.")

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise UnauthorizedException("Invalid token payload.")

        try:
            user_id = uuid.UUID(user_id_str)
        except (ValueError, TypeError):
            raise UnauthorizedException("Invalid user identifier in token.")

        user = await self.user_repo.get_by_id(db, user_id)
        if not user or not user.is_active:
            raise UnauthorizedException("User not found or inactive.")

        # Invalidate old refresh token (Token Rotation)
        exp = payload.get("exp", 0)
        remaining_ttl = max(int(exp - time.time()), 1)
        await blacklist_token(jti, remaining_ttl)

        # Issue new token pair
        new_access_token = create_access_token(user.id)
        new_refresh_token, _ = create_refresh_token(user.id)

        return TokenRefreshResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, refresh_token_str: str) -> None:
        try:
            payload = decode_token(refresh_token_str)
            if payload.get("type") == "refresh":
                jti = payload.get("jti")
                exp = payload.get("exp", 0)
                if jti:
                    remaining_ttl = max(int(exp - time.time()), 1)
                    await blacklist_token(jti, remaining_ttl)
        except Exception:
            # If token is invalid or expired, logout is considered successful
            pass

    async def request_password_reset(
        self,
        db: AsyncSession,
        email: str,
    ) -> Optional[tuple[str, Optional[str]]]:
        clean_email = email.lower().strip()
        user = await self.user_repo.get_by_email(db, clean_email)
        if not user:
            return None

        otp = generate_otp()
        await store_password_reset_otp(
            email=clean_email,
            user_id=user.id,
            otp=otp,
            expire_seconds=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES * 60,
        )
        return otp, user.username

    async def reset_password(
        self,
        db: AsyncSession,
        payload: ResetPasswordRequest,
    ) -> None:
        user_id: Optional[uuid.UUID] = None
        raw_token = payload.token.strip()

        # 1. Try OTP verification (works with or without email)
        if len(raw_token) == 6 and raw_token.isdigit():
            user_id = await verify_password_reset_otp(str(payload.email) if payload.email else None, raw_token)

        # 2. If not found, try JWT token verification for backward compatibility
        if not user_id:
            try:
                token_payload = decode_token(raw_token)
                if token_payload.get("type") == "password_reset":
                    user_id_str = token_payload.get("sub")
                    if user_id_str:
                        user_id = uuid.UUID(user_id_str)
            except Exception:
                pass

        if not user_id:
            raise UnauthorizedException("Invalid or expired verification code or token.")

        user = await self.user_repo.get_by_id(db, user_id)
        if not user:
            raise UnauthorizedException("User not found.")

        hashed_password = get_password_hash(payload.new_password)
        await self.user_repo.update_password(db, user, hashed_password)

    async def change_password(
        self,
        db: AsyncSession,
        user: User,
        payload: ChangePasswordRequest,
    ) -> None:
        if not verify_password(payload.current_password, user.hashed_password):
            raise BadRequestException("Current password is incorrect.")

        if payload.current_password == payload.new_password:
            raise BadRequestException("New password cannot be the same as the current password.")

        hashed_password = get_password_hash(payload.new_password)
        await self.user_repo.update_password(db, user, hashed_password)


auth_service = AuthService()
