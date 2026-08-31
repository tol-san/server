from __future__ import annotations

import json
import logging
import secrets
import time
import uuid
from typing import Optional
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

# Fallback in-memory storage for test/offline environments: key -> (data_dict, expiry_timestamp)
_in_memory_otp: dict[str, tuple[dict, float]] = {}
_MAX_MEMORY_OTP_SIZE = 500  # Maximum pending OTPs in memory fallback

def _cleanup_in_memory_otp() -> None:
    """Remove expired entries from in-memory OTP store."""
    now = time.time()
    expired = [k for k, (_, exp) in _in_memory_otp.items() if now >= exp]
    for k in expired:
        del _in_memory_otp[k]
    if len(_in_memory_otp) >= _MAX_MEMORY_OTP_SIZE:
        oldest = sorted(_in_memory_otp.items(), key=lambda x: x[1][1])[:_MAX_MEMORY_OTP_SIZE // 2]
        for k, _ in oldest:
            del _in_memory_otp[k]



def generate_otp() -> str:
    """Generate a cryptographically secure 6-digit numeric verification code."""
    return f"{secrets.randbelow(900000) + 100000}"


async def store_password_reset_otp(
    email: str,
    user_id: uuid.UUID,
    otp: str,
    expire_seconds: int = 420,  # 7 minutes default
) -> None:
    """
    Store 6-digit OTP in Redis with expiration time.
    The code is bound to the normalized email address. It is deliberately not
    indexed globally by code because a six-digit value is not an account
    identifier and must never be sufficient to choose a reset target.
    """
    clean_email = email.lower().strip()
    data = {
        "otp": otp,
        "user_id": str(user_id),
        "email": clean_email,
    }

    try:
        client: aioredis.Redis = get_redis_client()
        await client.set(
            f"otp:reset:{clean_email}",
            json.dumps(data),
            ex=expire_seconds,
        )
        logger.debug("[OTP] Stored reset OTP in Redis for %s (TTL: %ds)", clean_email, expire_seconds)
    except Exception as exc:
        logger.warning("[OTP] Redis store failed, falling back to memory: %s", exc)
        _cleanup_in_memory_otp()
        _in_memory_otp[clean_email] = (data, time.time() + expire_seconds)


async def verify_password_reset_otp(
    email: str,
    otp: str,
) -> Optional[uuid.UUID]:
    """
    Verify the 6-digit OTP for the given email address.
    If valid, consumes the OTP (deletes it) and returns the associated user_id.
    """
    clean_email = email.lower().strip()
    clean_otp = otp.strip()

    # 1. Check fallback in-memory cache
    if clean_email in _in_memory_otp:
        data, expires_at = _in_memory_otp[clean_email]
        if time.time() < expires_at and data.get("otp") == clean_otp:
            del _in_memory_otp[clean_email]
            return uuid.UUID(data["user_id"])

    # 2. Check Redis
    try:
        client: aioredis.Redis = get_redis_client()
        raw_data = await client.get(f"otp:reset:{clean_email}")

        if not raw_data:
            return None

        data = json.loads(raw_data)
        if data.get("otp") == clean_otp:
            await client.delete(f"otp:reset:{clean_email}")
            return uuid.UUID(data["user_id"])
        return None
    except Exception as exc:
        logger.warning("[OTP] Redis verify check failed: %s", exc)
        return None


async def store_password_reset_grant(
    jti: str,
    user_id: uuid.UUID,
    email: str,
    expire_seconds: int,
) -> None:
    """Persist a one-time grant backing a signed password-reset JWT."""
    key = f"password-reset-grant:{jti}"
    data = {"user_id": str(user_id), "email": email.lower().strip()}
    try:
        client: aioredis.Redis = get_redis_client()
        await client.set(key, json.dumps(data), ex=expire_seconds)
    except Exception as exc:
        logger.warning("Password reset grant store failed, using memory: %s", exc)
        _cleanup_in_memory_otp()
        _in_memory_otp[key] = (data, time.time() + expire_seconds)


async def consume_password_reset_grant(
    jti: str,
    user_id: uuid.UUID,
    email: str,
) -> bool:
    """Atomically consume and validate a one-time password-reset grant."""
    key = f"password-reset-grant:{jti}"
    expected_email = email.lower().strip()

    if key in _in_memory_otp:
        data, expires_at = _in_memory_otp.pop(key)
        return (
            time.time() < expires_at
            and data.get("user_id") == str(user_id)
            and data.get("email") == expected_email
        )

    try:
        client: aioredis.Redis = get_redis_client()
        raw_data = await client.getdel(key)
        if not raw_data:
            return False
        data = json.loads(raw_data)
        return (
            data.get("user_id") == str(user_id)
            and data.get("email") == expected_email
        )
    except Exception as exc:
        logger.warning("Password reset grant consume failed: %s", exc)
        return False


async def store_signup_otp(
    email: str,
    hashed_password: str,
    otp: str,
    expire_seconds: int = 420,  # 7 minutes default
) -> None:
    """
    Store 6-digit OTP for pending user registration in Redis.
    Holds email, hashed_password, and OTP.
    """
    clean_email = email.lower().strip()
    data = {
        "otp": otp,
        "email": clean_email,
        "hashed_password": hashed_password,
    }

    try:
        client: aioredis.Redis = get_redis_client()
        await client.set(
            f"otp:signup:{clean_email}",
            json.dumps(data),
            ex=expire_seconds,
        )
        logger.debug("[OTP] Stored signup OTP in Redis for %s (TTL: %ds)", clean_email, expire_seconds)
    except Exception as exc:
        logger.warning("[OTP] Redis store failed for signup, falling back to memory: %s", exc)
        _cleanup_in_memory_otp()
        _in_memory_otp[f"signup:{clean_email}"] = (data, time.time() + expire_seconds)


async def verify_signup_otp(
    email: str,
    otp: str,
) -> Optional[dict]:
    """
    Verify the 6-digit signup OTP for the given email address.
    If valid, consumes the OTP and returns the dict with 'email' and 'hashed_password'.
    """
    clean_email = email.lower().strip()
    clean_otp = otp.strip()

    # 1. Check in-memory fallback
    mem_key = f"signup:{clean_email}"
    if mem_key in _in_memory_otp:
        data, expires_at = _in_memory_otp[mem_key]
        if time.time() < expires_at and data.get("otp") == clean_otp:
            del _in_memory_otp[mem_key]
            return data

    # 2. Check Redis
    try:
        client: aioredis.Redis = get_redis_client()
        raw_data = await client.get(f"otp:signup:{clean_email}")
        if not raw_data:
            return None

        data = json.loads(raw_data)
        if data.get("otp") == clean_otp:
            await client.delete(f"otp:signup:{clean_email}")
            return data
        return None
    except Exception as exc:
        logger.warning("[OTP] Redis signup verify failed: %s", exc)
        return None
