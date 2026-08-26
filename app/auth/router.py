from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    TokenRefreshResponse,
    TokenResponse,
    UserRegisterRequest,
    UserResponse,
)
from app.auth.service import AuthService, auth_service
from app.core.config import settings
from app.core.database import get_db
from app.users.models import User

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


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate with email or username and password to obtain JWT access and refresh token pair.",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(lambda: auth_service),
) -> TokenResponse:
    return await service.login(db, payload)


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access token and rotated refresh token.",
)
async def refresh_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(lambda: auth_service),
) -> TokenRefreshResponse:
    return await service.refresh_tokens(db, payload.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    description="Revoke the provided refresh token and invalidate the active session.",
)
async def logout(
    payload: RefreshTokenRequest,
    service: AuthService = Depends(lambda: auth_service),
) -> MessageResponse:
    await service.logout(payload.refresh_token)
    return MessageResponse(message="Successfully logged out.")


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
    description="Generate a password reset token for the specified email address.",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(lambda: auth_service),
) -> ForgotPasswordResponse:
    token = await service.request_password_reset(db, payload.email)
    message = "If this email is registered, password reset instructions have been generated."
    # In development mode, return the token in response to allow rapid testing
    reset_token = token if settings.DEBUG else None
    return ForgotPasswordResponse(message=message, reset_token=reset_token)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset password with token",
    description="Set a new password using a verified password reset token.",
)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(lambda: auth_service),
) -> MessageResponse:
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
