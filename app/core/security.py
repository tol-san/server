from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
import uuid
import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.core.exceptions import UnauthorizedException

password_hash = PasswordHash.recommended()


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using Argon2."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(
    subject: Union[str, uuid.UUID],
    token_version: int = 0,
    expires_delta: Optional[timedelta] = None,
    jti: Optional[str] = None,
) -> str:
    """Create a stateless JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "access",
        "ver": token_version,
        "iat": now,
        "exp": expire,
    }
    if jti:
        payload["jti"] = jti
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)



def create_refresh_token(
    subject: Union[str, uuid.UUID],
    token_version: int = 0,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, str]:
    """Create a JWT refresh token with unique jti identifier."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "refresh",
        "jti": jti,
        "ver": token_version,
        "iat": now,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti


def create_password_reset_token(
    user_id: Union[str, uuid.UUID],
    email: str,
) -> tuple[str, str]:
    """Create a signed short-lived token for password reset."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "type": "password_reset",
        "jti": jti,
        "iat": now,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate signature and expiration of a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Token has expired.")
    except jwt.InvalidTokenError:
        raise UnauthorizedException("Invalid token.")
