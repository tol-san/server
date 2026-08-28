from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
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
    otp, clean_email = await service.request_signup_otp(db, payload.email, payload.password)
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
    payload: Optional[RefreshTokenRequest] = None,
    service: AuthService = Depends(lambda: auth_service),
) -> MessageResponse:
    if payload and payload.refresh_token:
        await service.logout(payload.refresh_token)
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
    result = await service.request_password_reset(db, payload.email)
    if result:
        otp, username = result
        background_tasks.add_task(send_password_reset_otp_email, payload.email, otp, username)
        reset_token = otp if settings.DEBUG else None
    else:
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
