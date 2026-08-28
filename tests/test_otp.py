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
