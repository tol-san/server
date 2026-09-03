import re
import secrets
import time
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime, timezone
from sqlalchemy import select, update

from app.auth.models import UserSession
from app.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    TokenRefreshResponse,
    TokenResponse,
    UserRegisterRequest,
    UserResponse,
    UserSessionResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.core.config import settings
from app.core.email_verifier import verify_email_deliverability
from app.core.exceptions import (
    BadRequestException,
    EmailAlreadyExistsException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
    UsernameAlreadyExistsException,
)
from app.core.otp import (
    consume_password_reset_grant,
    generate_otp,
    store_password_reset_grant,
    store_password_reset_otp,
    store_signup_otp,
    verify_password_reset_otp,
    verify_signup_otp,
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

    @staticmethod
    async def _index_user_to_search(user: "User") -> None:
        """Index the user in Meilisearch. Logs warning on failure but does not raise."""
        try:
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
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "[Search] Failed to index user %s in Meilisearch: %s",
                user.id,
                exc,
            )

    async def generate_unique_username(self, db: AsyncSession, email: str) -> str:
        """
        Derive a clean, unique alphanumeric username from the email prefix.
        Appends incremental counters or random numbers if collisions occur.
        """
        prefix = email.split("@")[0].lower().strip()
        cleaned = re.sub(r"[^a-z0-9_]", "_", prefix)
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        if not cleaned:
            cleaned = "user"

        base_username = cleaned[:20]
        candidate = base_username

        # Check if base username is already available
        existing = await self.user_repo.get_by_username(db, candidate)
        if not existing:
            return candidate

        # Append counter
        counter = 1
        while True:
            candidate = f"{base_username}_{counter}"
            existing = await self.user_repo.get_by_username(db, candidate)
            if not existing:
                return candidate
            counter += 1
            if counter > 50:
                # Add random suffix if counter runs high
                candidate = f"{base_username}_{secrets.randbelow(9000) + 1000}"
                return candidate

    async def check_username_available(self, db: AsyncSession, username: str) -> bool:
        """Check if a candidate username is available in PostgreSQL."""
        clean_username = username.lower().strip()
        user = await self.user_repo.get_by_username(db, clean_username)
        return user is None

    async def request_signup_otp(
        self,
        db: AsyncSession,
        email: str,
        password: str,
    ) -> tuple[str, str]:
        """
        Initiate two-step signup by checking deliverability, hashing password,
        generating 6-digit OTP, and storing in Redis for 7 minutes.
        """
        clean_email = email.lower().strip()
        existing_user = await self.user_repo.get_by_email(db, clean_email)
        if existing_user:
            raise EmailAlreadyExistsException("A user with this email already exists.")

        clean_email = await verify_email_deliverability(clean_email)

        hashed_password = get_password_hash(password)
        otp = generate_otp()
        await store_signup_otp(
            clean_email,
            hashed_password,
            otp,
            expire_seconds=settings.SIGNUP_OTP_EXPIRE_MINUTES * 60,
        )
        return otp, clean_email

    async def verify_signup_otp_and_create_user(
        self,
        db: AsyncSession,
        email: str,
        otp: str,
    ) -> TokenResponse:
        """
        Verify signup OTP from Redis, generate unique username, create user and profile in DB,
        and issue JWT token pair.
        """
        clean_email = email.lower().strip()
        existing_user = await self.user_repo.get_by_email(db, clean_email)
        if existing_user:
            raise EmailAlreadyExistsException("A user with this email already exists.")

        data = await verify_signup_otp(clean_email, otp)
        if not data:
            raise BadRequestException("Invalid or expired verification code.")

        hashed_password = data.get("hashed_password")
        if not hashed_password:
            raise BadRequestException("Signup session expired or corrupted. Please sign up again.")

        username = await self.generate_unique_username(db, clean_email)

        # Derive initial default display name from email prefix
        raw_prefix = clean_email.split("@")[0]
        display_name = re.sub(r"[._-]+", " ", raw_prefix).strip().title()
        if not display_name:
            display_name = username

        user = await self.user_repo.create_user_with_profile(
            db,
            email=clean_email,
            username=username,
            hashed_password=hashed_password,
            display_name=display_name,
        )

        await self._index_user_to_search(user)

        refresh_token, jti = create_refresh_token(user.id, user.token_version)
        access_token = create_access_token(user.id, user.token_version, jti=jti)

        await self._record_session(db, user.id, jti, None, None)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user),
        )

    async def register_user(
        self,
        db: AsyncSession,
        payload: UserRegisterRequest,
    ) -> User:
        clean_email = payload.email.lower().strip()
        # Check if email is already taken
        existing_user_by_email = await self.user_repo.get_by_email(db, clean_email)
        if existing_user_by_email:
            raise EmailAlreadyExistsException("A user with this email already exists.")

        # If username is omitted, auto-generate unique username
        if payload.username:
            clean_username = payload.username.lower().strip()
            existing_user_by_username = await self.user_repo.get_by_username(db, clean_username)
            if existing_user_by_username:
                raise UsernameAlreadyExistsException("A user with this username already exists.")
            username = clean_username
        else:
            username = await self.generate_unique_username(db, clean_email)

        # Hash password securely
        hashed_password = get_password_hash(payload.password)

        display_name = payload.display_name or (payload.username if payload.username else None)
        if not display_name:
            raw_prefix = clean_email.split("@")[0]
            display_name = re.sub(r"[._-]+", " ", raw_prefix).strip().title()

        # Create user with profile
        user = await self.user_repo.create_user_with_profile(
            db,
            email=clean_email,
            username=username,
            hashed_password=hashed_password,
            display_name=display_name,
        )

        await self._index_user_to_search(user)

        return user

    async def login(
        self,
        db: AsyncSession,
        payload: LoginRequest,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        user = await self.user_repo.get_by_email_or_username(db, payload.identifier)
        if not user:
            raise UnauthorizedException("Invalid email/username or password.")

        if not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedException("Invalid email/username or password.")

        if not user.is_active:
            raise ForbiddenException("User account is deactivated.")

        refresh_token, jti = create_refresh_token(user.id, user.token_version)
        access_token = create_access_token(user.id, user.token_version, jti=jti)

        await self._record_session(db, user.id, jti, client_ip, user_agent)

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
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
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
        if payload.get("ver") != user.token_version:
            raise UnauthorizedException("Refresh token has been revoked or is invalid.")

        # Invalidate old refresh token (Token Rotation)
        exp = payload.get("exp", 0)
        remaining_ttl = max(int(exp - time.time()), 1)
        await blacklist_token(jti, remaining_ttl)

        # Issue new token pair
        new_refresh_token, new_jti = create_refresh_token(user.id, user.token_version)
        new_access_token = create_access_token(user.id, user.token_version, jti=new_jti)

        # Rotate session in DB
        now = datetime.now(timezone.utc)
        stmt = (
            update(UserSession)
            .where(UserSession.refresh_jti == jti)
            .values(
                refresh_jti=new_jti,
                last_active_at=now,
                ip_address=client_ip if client_ip else UserSession.ip_address,
                user_agent=user_agent if user_agent else UserSession.user_agent,
            )
        )
        await db.execute(stmt)
        await db.commit()

        return TokenRefreshResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, db: AsyncSession, refresh_token_str: str) -> None:
        try:
            payload = decode_token(refresh_token_str)
            if payload.get("type") == "refresh":
                jti = payload.get("jti")
                exp = payload.get("exp", 0)
                if jti:
                    remaining_ttl = max(int(exp - time.time()), 1)
                    await blacklist_token(jti, remaining_ttl)
                    # Mark session revoked in DB
                    stmt = (
                        update(UserSession)
                        .where(UserSession.refresh_jti == jti)
                        .values(is_revoked=True)
                    )
                    await db.execute(stmt)
                    await db.commit()
        except Exception:
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

    async def verify_otp(
        self,
        db: AsyncSession,
        payload: VerifyOtpRequest,
    ) -> VerifyOtpResponse:
        clean_email = payload.email.lower().strip()
        raw_otp = payload.otp.strip()

        user_id = await verify_password_reset_otp(clean_email, raw_otp)
        if not user_id:
            raise UnauthorizedException("Invalid or expired verification code.")

        user = await self.user_repo.get_by_id(db, user_id)
        if not user or not user.is_active:
            raise UnauthorizedException("User account is inactive or not found.")

        reset_token, reset_jti = create_password_reset_token(user.id, user.email)
        await store_password_reset_grant(
            reset_jti,
            user.id,
            user.email,
            settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES * 60,
        )

        return VerifyOtpResponse(
            reset_token=reset_token,
            expires_in=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def reset_password(
        self,
        db: AsyncSession,
        payload: ResetPasswordRequest,
    ) -> None:
        raw_token = payload.token.strip() if payload.token else ""
        token_payload = decode_token(raw_token)
        if token_payload.get("type") != "password_reset":
            raise UnauthorizedException("Invalid token type. Expected password reset token.")
        try:
            user_id = uuid.UUID(token_payload["sub"])
            token_email = str(token_payload["email"])
            jti = str(token_payload["jti"])
        except (KeyError, TypeError, ValueError):
            raise UnauthorizedException("Invalid password reset token.")

        if not await consume_password_reset_grant(jti, user_id, token_email):
            raise UnauthorizedException("Password reset token is invalid, expired, or already used.")

        user = await self.user_repo.get_by_id(db, user_id)
        if not user or user.email.lower() != token_email.lower():
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

    def _parse_device_name(self, user_agent: Optional[str]) -> str:
        if not user_agent:
            return "Unknown Device"
        ua = user_agent.lower()
        if "dart" in ua or "flutter" in ua:
            if "android" in ua:
                return "Flutter App (Android)"
            if "iphone" in ua or "ipad" in ua:
                return "Flutter App (iOS)"
            return "GenZ Media App"
        if "iphone" in ua:
            return "iPhone"
        if "ipad" in ua:
            return "iPad"
        if "android" in ua:
            return "Android Device"
        if "macintosh" in ua or "mac os" in ua:
            return "Mac"
        if "windows" in ua:
            return "Windows PC"
        if "linux" in ua:
            return "Linux PC"
        return "Web Browser"

    async def _record_session(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        refresh_jti: str,
        client_ip: Optional[str],
        user_agent: Optional[str],
    ) -> UserSession:
        device_name = self._parse_device_name(user_agent)
        now = datetime.now(timezone.utc)
        session = UserSession(
            user_id=user_id,
            refresh_jti=refresh_jti,
            ip_address=client_ip,
            user_agent=user_agent,
            device_name=device_name,
            last_active_at=now,
            created_at=now,
            is_revoked=False,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def get_user_sessions(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        current_jti: Optional[str] = None,
    ) -> list[UserSessionResponse]:
        stmt = (
            select(UserSession)
            .where(UserSession.user_id == user_id, UserSession.is_revoked.is_(False))
            .order_by(UserSession.last_active_at.desc())
        )
        result = await db.execute(stmt)
        sessions = result.scalars().all()
        return [
            UserSessionResponse(
                id=s.id,
                device_name=s.device_name,
                ip_address=s.ip_address,
                last_active_at=s.last_active_at,
                created_at=s.created_at,
                is_current=(s.refresh_jti == current_jti),
            )
            for s in sessions
        ]

    async def revoke_session(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> None:
        stmt = select(UserSession).where(
            UserSession.id == session_id,
            UserSession.user_id == user_id,
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        if not session or session.is_revoked:
            raise NotFoundException("Session not found.")

        session.is_revoked = True
        await db.commit()
        await blacklist_token(session.refresh_jti, settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)

    async def revoke_other_sessions(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        current_jti: Optional[str] = None,
    ) -> int:
        stmt = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_revoked.is_(False),
        )
        if current_jti:
            stmt = stmt.where(UserSession.refresh_jti != current_jti)

        result = await db.execute(stmt)
        sessions = result.scalars().all()
        for s in sessions:
            s.is_revoked = True
            await blacklist_token(s.refresh_jti, settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)

        await db.commit()
        return len(sessions)


auth_service = AuthService()

