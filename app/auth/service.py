from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import UserRegisterRequest
from app.core.exceptions import (
    EmailAlreadyExistsException,
    UsernameAlreadyExistsException,
)
from app.core.security import get_password_hash
from app.users.models import User
from app.users.repository import UserRepository, user_repository


class AuthService:
    """Service handling authentication business logic."""

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

        return user


auth_service = AuthService()
