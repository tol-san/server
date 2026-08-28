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


def generate_otp() -> str:
    """Generate a cryptographically secure 6-digit numeric verification code."""
    return f"{secrets.randbelow(900000) + 100000}"


async def store_password_reset_otp(
    email: str,
    user_id: uuid.UUID,
    otp: str,
    expire_seconds: int = 900,  # 15 minutes default
) -> None:
    """
    Store 6-digit OTP in Redis with expiration time.
    Indexed by both email and OTP code for flexible verification.
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
        await client.set(
            f"otp:code:{otp}",
            json.dumps(data),
            ex=expire_seconds,
        )
        logger.debug("[OTP] Stored reset OTP in Redis for %s (TTL: %ds)", clean_email, expire_seconds)
    except Exception as exc:
        logger.warning("[OTP] Redis store failed, falling back to memory: %s", exc)
        _in_memory_otp[clean_email] = (data, time.time() + expire_seconds)
        _in_memory_otp[f"code:{otp}"] = (data, time.time() + expire_seconds)


async def verify_password_reset_otp(
    email: Optional[str],
    otp: str,
) -> Optional[uuid.UUID]:
    """
    Verify the 6-digit OTP for the given email address or OTP code.
    If valid, consumes the OTP (deletes it) and returns the associated user_id.
    """
    clean_email = email.lower().strip() if email else None
    clean_otp = otp.strip()

    # 1. Check fallback in-memory cache
    if clean_email and clean_email in _in_memory_otp:
        data, expires_at = _in_memory_otp[clean_email]
        if time.time() < expires_at and data.get("otp") == clean_otp:
            del _in_memory_otp[clean_email]
            if f"code:{clean_otp}" in _in_memory_otp:
                del _in_memory_otp[f"code:{clean_otp}"]
            return uuid.UUID(data["user_id"])
    elif f"code:{clean_otp}" in _in_memory_otp:
        data, expires_at = _in_memory_otp[f"code:{clean_otp}"]
        if time.time() < expires_at:
            del _in_memory_otp[f"code:{clean_otp}"]
            if data.get("email") and data["email"] in _in_memory_otp:
                del _in_memory_otp[data["email"]]
            return uuid.UUID(data["user_id"])

    # 2. Check Redis
    try:
        client: aioredis.Redis = get_redis_client()
        raw_data = None
        if clean_email:
            raw_data = await client.get(f"otp:reset:{clean_email}")
        if not raw_data:
            raw_data = await client.get(f"otp:code:{clean_otp}")

        if not raw_data:
            return None

        data = json.loads(raw_data)
        if data.get("otp") == clean_otp:
            if data.get("email"):
                await client.delete(f"otp:reset:{data['email']}")
            await client.delete(f"otp:code:{clean_otp}")
            return uuid.UUID(data["user_id"])
        return None
    except Exception as exc:
        logger.warning("[OTP] Redis verify check failed: %s", exc)
        return None
