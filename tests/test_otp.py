import uuid
import pytest
from app.core.otp import generate_otp, store_password_reset_otp, verify_password_reset_otp


@pytest.mark.asyncio
async def test_generate_otp():
    otp = generate_otp()
    assert len(otp) == 6
    assert otp.isdigit()


@pytest.mark.asyncio
async def test_store_and_verify_otp_success():
    email = "user_test_otp@example.com"
    user_id = uuid.uuid4()
    otp = generate_otp()

    await store_password_reset_otp(email, user_id, otp, expire_seconds=60)

    # Correct OTP should return the user_id
    verified_id = await verify_password_reset_otp(email, otp)
    assert verified_id == user_id

    # Single-use: Second attempt should fail
    second_attempt = await verify_password_reset_otp(email, otp)
    assert second_attempt is None


@pytest.mark.asyncio
async def test_verify_wrong_otp_fails():
    email = "user_wrong_otp@example.com"
    user_id = uuid.uuid4()
    otp = "123456"

    await store_password_reset_otp(email, user_id, otp, expire_seconds=60)

    # Wrong OTP
    verified_id = await verify_password_reset_otp(email, "654321")
    assert verified_id is None


@pytest.mark.asyncio
async def test_verify_otp_endpoint(async_client):
    test_email = "otp_verify_flow@example.com"
    # Register user
    reg_resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": test_email,
            "username": "otp_flow_user",
            "password": "Password123!",
        },
    )
    assert reg_resp.status_code in (200, 201)

    # 1. Request OTP
    forgot_resp = await async_client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_email},
    )
    assert forgot_resp.status_code == 200
    assert forgot_resp.json()["reset_token"] is None

    # Retrieve generated OTP from Redis / memory store
    import json
    from app.core.redis import get_redis_client
    from app.core.otp import _in_memory_otp

    otp = None
    try:
        client = get_redis_client()
        raw = await client.get(f"otp:reset:{test_email}")
        if raw:
            otp = json.loads(raw).get("otp")
    except Exception:
        pass
    if not otp and test_email in _in_memory_otp:
        otp = _in_memory_otp[test_email][0].get("otp")

    assert otp is not None
    assert len(otp) == 6

    # 2. Verify OTP endpoint -> logs in and returns tokens
    verify_resp = await async_client.post(
        "/api/v1/auth/verify-otp",
        json={"email": test_email, "otp": otp},
    )
    assert verify_resp.status_code == 200
    data = verify_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "reset_token" in data
    assert data["user"]["email"] == test_email

    # 3. Invalid OTP returns 401
    invalid_resp = await async_client.post(
        "/api/v1/auth/verify-otp",
        json={"email": test_email, "otp": "000000"},
    )
    assert invalid_resp.status_code == 401
