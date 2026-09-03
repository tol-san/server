import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.users.models import User
from app.users.schemas import (
    BlockActionResponse,
    DeactivateAccountRequest,
    DeleteAccountRequest,
    FollowActionResponse,
    PaginatedUsersResponse,
    RelationshipResponse,
    UserPrivacyResponse,
    UserPrivacyUpdateRequest,
    UserPublicResponse,
)
from app.auth.schemas import CheckUsernameResponse, MessageResponse
from app.auth.service import AuthService, auth_service
from app.users.service import UserService, user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/check-username",
    response_model=CheckUsernameResponse,
    status_code=status.HTTP_200_OK,
    summary="Check username availability",
    description="Check whether a given candidate username is currently available or already taken.",
)
async def check_username(
    username: str = Query(..., min_length=3, max_length=30, description="Username candidate to test"),
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(lambda: auth_service),
) -> CheckUsernameResponse:
    is_available = await service.check_username_available(db, username)
    return CheckUsernameResponse(available=is_available, username=username.lower().strip())


@router.get(
    "/me/blocked",
    response_model=PaginatedUsersResponse,
    status_code=status.HTTP_200_OK,
    summary="Get blocked users",
    description="Retrieve a paginated list of users blocked by the authenticated user.",
)
async def get_my_blocked_users(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(lambda: user_service),
) -> PaginatedUsersResponse:
    return await service.get_blocked_users(db, current_user, limit, offset)


@router.get(
    "/me/privacy",
    response_model=UserPrivacyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user privacy settings",
    description="Retrieve privacy settings for the authenticated user.",
)
async def get_privacy_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(lambda: user_service),
) -> UserPrivacyResponse:
    return await service.get_privacy_settings(db, current_user)


@router.patch(
    "/me/privacy",
    response_model=UserPrivacyResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user privacy settings",
    description="Update privacy preferences such as account visibility, comments, mentions, and search discoverability.",
)
async def update_privacy_settings(
    payload: UserPrivacyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(lambda: user_service),
) -> UserPrivacyResponse:
    return await service.update_privacy_settings(db, current_user, payload)


@router.post(
    "/me/deactivate",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate user account",
    description="Deactivate account, invalidating current sessions and excluding profile from public discovery.",
)
async def deactivate_account(
    payload: DeactivateAccountRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(lambda: user_service),
) -> MessageResponse:
    await service.deactivate_account(db, current_user, payload.password, payload.reason)
    return MessageResponse(message="Account successfully deactivated.")


@router.delete(
    "/me",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Permanently delete user account",
    description="Permanently delete user account, invalidating all credentials and cascading dependent records.",
)
async def delete_account(
    payload: DeleteAccountRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(lambda: user_service),
) -> MessageResponse:
    await service.delete_account(db, current_user, payload.password, payload.confirmation)
    return MessageResponse(message="Account successfully deleted.")


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


@router.post(
    "/{user_id}/follow",
    response_model=FollowActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Follow a user",
    description="Follow the specified user and increment social counters.",
)
async def follow_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(lambda: user_service),
) -> FollowActionResponse:
    return await service.follow_user(db, current_user, user_id)


@router.delete(
    "/{user_id}/follow",
    response_model=FollowActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Unfollow a user",
    description="Unfollow the specified user and decrement social counters.",
)
async def unfollow_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(lambda: user_service),
) -> FollowActionResponse:
    return await service.unfollow_user(db, current_user, user_id)


@router.post(
    "/{user_id}/block",
    response_model=BlockActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Block a user",
    description="Block a user and automatically sever any mutual follow relationships.",
)
async def block_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(lambda: user_service),
) -> BlockActionResponse:
    return await service.block_user(db, current_user, user_id)


@router.delete(
    "/{user_id}/block",
    response_model=BlockActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Unblock a user",
    description="Unblock a previously blocked user.",
)
async def unblock_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(lambda: user_service),
) -> BlockActionResponse:
    return await service.unblock_user(db, current_user, user_id)


@router.get(
    "/{user_id}/followers",
    response_model=PaginatedUsersResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user followers",
    description="Retrieve a paginated list of users who follow the specified user.",
)
async def get_user_followers(
    user_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    service: UserService = Depends(lambda: user_service),
) -> PaginatedUsersResponse:
    return await service.get_followers(db, user_id, limit, offset)


@router.get(
    "/{user_id}/following",
    response_model=PaginatedUsersResponse,
    status_code=status.HTTP_200_OK,
    summary="Get users followed by user",
    description="Retrieve a paginated list of users that the specified user is following.",
)
async def get_user_following(
    user_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    service: UserService = Depends(lambda: user_service),
) -> PaginatedUsersResponse:
    return await service.get_following(db, user_id, limit, offset)


@router.get(
    "/{user_id}/relationship",
    response_model=RelationshipResponse,
    status_code=status.HTTP_200_OK,
    summary="Get relationship status",
    description="Retrieve directional follow and block status between the authenticated user and target user.",
)
async def get_user_relationship(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(lambda: user_service),
) -> RelationshipResponse:
    return await service.get_relationship(db, current_user, user_id)
