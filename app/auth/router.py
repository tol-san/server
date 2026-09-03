import uuid
from typing import Optional
import hashlib
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, status, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user, get_current_jti, get_current_user
from app.core.cache import cache_service

logger = logging.getLogger(__name__)

async def _rate_limit(key: str, max_requests: int, window_seconds: int) -> None:
    """Simple Redis-backed rate limiter. Raises 429 if limit exceeded."""
    count = await cache_service.incr(key)
    if count == 1:
        # First request in window — set the TTL
        await cache_service.set(key, count, ttl=window_seconds)
    if count > max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait and retry.",
        )
from app.auth.schemas import (
    ChangePasswordRequest,
    CheckUsernameResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    SignupOtpRequest,
    SignupOtpResponse,
    SignupVerifyOtpRequest,
    TokenRefreshResponse,
    TokenResponse,
    UserRegisterRequest,
    UserResponse,
    UserSessionResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.auth.service import AuthService, auth_service
from app.core.config import settings
from app.core.database import get_db
from app.core.email import (
    send_password_reset_email,
    send_password_reset_otp_email,
    send_signup_otp_email,
)
from app.users.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register/request-otp",
    response_model=SignupOtpResponse,
    status_code=status.HTTP_200_OK,
    summary="Request registration OTP code",
    description="Initiate two-step signup by sending a 6-digit verification code to the specified email address.",
)
async def request_signup_otp(
    payload: SignupOtpRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(lambda: auth_service),
) -> SignupOtpResponse:
    await _rate_limit(f"ratelimit:signup_otp:{payload.email.lower()}", max_requests=5, window_seconds=60)
    otp, clean_email = await service.request_signup_otp(db, payload.email, payload.password)
    if settings.SMTP_HOST:
        await send_signup_otp_email(clean_email, otp)
    else:
        background_tasks.add_task(send_signup_otp_email, clean_email, otp)

    return SignupOtpResponse(
        message="Verification code sent to your email address.",
        email=clean_email,
        expires_in=settings.SIGNUP_OTP_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/register/verify-otp",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Verify registration OTP and create account",
    description="Verify the 6-digit signup OTP code, generate unique username, create user and profile in database, and issue session tokens.",
)
async def verify_signup_otp(
    payload: SignupVerifyOtpRequest,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(lambda: auth_service),
) -> TokenResponse:
    await _rate_limit(f"ratelimit:verify_signup_otp:{payload.email.lower()}", max_requests=5, window_seconds=300)
    return await service.verify_signup_otp_and_create_user(db, payload.email, payload.otp)


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


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate with email or username and password to obtain JWT access and refresh token pair.",
)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(lambda: auth_service),
) -> TokenResponse:
    await _rate_limit(f"ratelimit:login:{payload.identifier.lower()}", max_requests=10, window_seconds=60)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.login(db, payload, client_ip=client_ip, user_agent=user_agent)


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access token and rotated refresh token.",
)
async def refresh_token(
    payload: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(lambda: auth_service),
) -> TokenRefreshResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.refresh_tokens(db, payload.refresh_token, client_ip=client_ip, user_agent=user_agent)


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    description="Revoke the provided refresh token and invalidate the active session.",
)
async def logout(
    payload: Optional[RefreshTokenRequest] = None,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(lambda: auth_service),
) -> MessageResponse:
    if payload and payload.refresh_token:
        await service.logout(db, payload.refresh_token)
    return MessageResponse(message="Successfully logged out.")


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
    description="Generate a 6-digit verification code for the specified email address and dispatch email instructions.",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(lambda: auth_service),
) -> ForgotPasswordResponse:
    await _rate_limit(f"ratelimit:forgot_password:{payload.email.lower()}", max_requests=3, window_seconds=300)
    result = await service.request_password_reset(db, payload.email)
    if result:
        otp, username = result
        background_tasks.add_task(send_password_reset_otp_email, payload.email, otp, username)
        
    # Never expose OTP in response body — security risk even in DEBUG mode
    reset_token = None

    message = "If this email is registered, verification instructions have been generated."
    return ForgotPasswordResponse(message=message, reset_token=reset_token)


@router.post(
    "/verify-otp",
    response_model=VerifyOtpResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify 6-digit OTP verification code",
    description="Validate the 6-digit verification code, authenticate the user session, and issue access tokens.",
)
async def verify_otp(
    payload: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(lambda: auth_service),
) -> VerifyOtpResponse:
    await _rate_limit(f"ratelimit:verify_otp:{payload.email.lower()}", max_requests=5, window_seconds=300)
    return await service.verify_otp(db, payload)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset password with token",
    description="Set a new password using a verified password reset token.",
)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(lambda: auth_service),
) -> MessageResponse:
    token_fingerprint = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    client_host = request.client.host if request.client else "unknown"
    await _rate_limit(
        f"ratelimit:reset_password:{client_host}:{token_fingerprint}",
        max_requests=5,
        window_seconds=300,
    )
    await service.reset_password(db, payload)
    return MessageResponse(message="Password has been successfully reset. You can now login.")


@router.post(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change password",
    description="Change password for the currently authenticated user.",
)
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(lambda: auth_service),
) -> MessageResponse:
    await service.change_password(db, current_user, payload)
    return MessageResponse(message="Password changed successfully.")


@router.get(
    "/sessions",
    response_model=list[UserSessionResponse],
    status_code=status.HTTP_200_OK,
    summary="List active user sessions",
    description="Retrieve all active signed-in devices and sessions for the authenticated user.",
)
async def get_my_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    current_jti: Optional[str] = Depends(get_current_jti),
    service: AuthService = Depends(lambda: auth_service),
) -> list[UserSessionResponse]:
    return await service.get_user_sessions(db, current_user.id, current_jti=current_jti)


@router.delete(
    "/sessions/other",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke all other sessions",
    description="Sign out from all other devices and sessions except the current one.",
)
async def revoke_other_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    current_jti: Optional[str] = Depends(get_current_jti),
    service: AuthService = Depends(lambda: auth_service),
) -> MessageResponse:
    count = await service.revoke_other_sessions(db, current_user.id, current_jti=current_jti)
    return MessageResponse(message=f"Successfully signed out of {count} other session(s).")


@router.delete(
    "/sessions/{session_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke a specific session",
    description="Revoke a specific signed-in device/session by ID.",
)
async def revoke_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(lambda: auth_service),
) -> MessageResponse:
    await service.revoke_session(db, current_user.id, session_id)
    return MessageResponse(message="Session successfully revoked.")
