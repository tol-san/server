import pytest
from app.core.otp import generate_otp, store_signup_otp, verify_signup_otp
from app.core.security import get_password_hash


@pytest.mark.asyncio
async def test_signup_otp_storage_and_verification():
    email = "signup_unit_test@example.com"
    pwd = get_password_hash("ValidPass123!")
    otp = generate_otp()

    await store_signup_otp(email, pwd, otp, expire_seconds=60)

    # 1. Verify correct OTP
    data = await verify_signup_otp(email, otp)
    assert data is not None
    assert data["email"] == email
    assert data["hashed_password"] == pwd

    # 2. Single-use check: second attempt should fail
    data2 = await verify_signup_otp(email, otp)
    assert data2 is None


@pytest.mark.asyncio
async def test_full_signup_otp_flow_endpoint(async_client):
    test_email = "alex_signup@genz.media"
    test_pwd = "StrongSecurePassword123!"

    # 1. Request Signup OTP
    req_resp = await async_client.post(
        "/api/v1/auth/register/request-otp",
        json={
            "email": test_email,
            "password": test_pwd,
        },
    )
    assert req_resp.status_code == 200
    assert req_resp.json()["email"] == test_email

    # Retrieve stored OTP from in-memory / redis mock
    from app.core.otp import _in_memory_otp, get_redis_client
    import json
    try:
        r = get_redis_client()
        raw = await r.get(f"otp:signup:{test_email}")
        if raw:
            otp = json.loads(raw)["otp"]
        else:
            otp = _in_memory_otp[f"signup:{test_email}"][0]["otp"]
    except Exception:
        otp = _in_memory_otp[f"signup:{test_email}"][0]["otp"]

    assert len(otp) == 6

    # 2. Verify Signup OTP & Create User
    verify_resp = await async_client.post(
        "/api/v1/auth/register/verify-otp",
        json={
            "email": test_email,
            "otp": otp,
        },
    )
    assert verify_resp.status_code == 201
    res_data = verify_resp.json()
    assert "access_token" in res_data
    assert "refresh_token" in res_data
    assert res_data["user"]["email"] == test_email
    assert res_data["user"]["username"] == "alex_signup"  # Auto-generated unique username
    assert res_data["user"]["profile"]["display_name"] == "Alex Signup"

    # 3. Check username endpoint
    check_resp = await async_client.get(
        "/api/v1/users/check-username",
        params={"username": "alex_signup"},
    )
    assert check_resp.status_code == 200
    assert check_resp.json()["available"] is False

    check_avail = await async_client.get(
        "/api/v1/users/check-username",
        params={"username": "brand_new_alex"},
    )
    assert check_avail.status_code == 200
    assert check_avail.json()["available"] is True


@pytest.mark.asyncio
async def test_duplicate_email_signup_fails(async_client):
    test_email = "duplicate_alex@genz.media"
    # Register first
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": test_email,
            "password": "Password123!",
        },
    )

    # Attempt to request signup OTP on existing email
    dup_resp = await async_client.post(
        "/api/v1/auth/register/request-otp",
        json={
            "email": test_email,
            "password": "NewPassword123!",
        },
    )
    assert dup_resp.status_code == 409  # EmailAlreadyExists


@pytest.mark.asyncio
async def test_invalid_syntax_email_signup_fails(async_client):
    invalid_resp = await async_client.post(
        "/api/v1/auth/register/request-otp",
        json={
            "email": "not-an-email",
            "password": "Password123!",
        },
    )
    assert invalid_resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_signup_otp_7_minute_expiry(async_client):
    req_resp = await async_client.post(
        "/api/v1/auth/register/request-otp",
        json={
            "email": "seven_min_expiry@genz.media",
            "password": "Password123!",
        },
    )
    assert req_resp.status_code == 200
    assert req_resp.json()["expires_in"] == 420  # 7 minutes = 420 seconds
