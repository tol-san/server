from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.email import send_email, send_password_reset_email


@pytest.mark.asyncio
async def test_send_email_success():
    with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (None, "OK")
        
        success = await send_email(
            to_email="testuser@example.com",
            subject="Test Subject",
            html_content="<p>Test HTML</p>",
            text_content="Test Text",
        )

        assert success is True
        assert mock_send.call_count == 1
        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["hostname"] == settings.SMTP_HOST
        assert call_kwargs["port"] == settings.SMTP_PORT
        assert call_kwargs["use_tls"] == settings.SMTP_USE_SSL
        assert call_kwargs["start_tls"] == settings.SMTP_STARTTLS

        # Verify email message
        message = mock_send.call_args.args[0]
        assert message["To"] == "testuser@example.com"
        assert message["Subject"] == "Test Subject"
        assert f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>" in message["From"]


@pytest.mark.asyncio
async def test_send_email_failure_handles_exception():
    with patch("aiosmtplib.send", side_effect=ConnectionRefusedError("SMTP server down")):
        success = await send_email(
            to_email="testuser@example.com",
            subject="Test Subject",
            html_content="<p>Test HTML</p>",
        )
        assert success is False


@pytest.mark.asyncio
async def test_send_password_reset_email():
    with patch("app.core.email.send_email", new_callable=AsyncMock) as mock_send_email:
        mock_send_email.return_value = True

        token = "mock_sample_jwt_reset_token_12345"
        success = await send_password_reset_email(
            to_email="alice@example.com",
            reset_token=token,
            username="alice",
        )

        assert success is True
        assert mock_send_email.call_count == 1
        kwargs = mock_send_email.call_args.kwargs
        assert kwargs["to_email"] == "alice@example.com"
        assert "Reset Your Password" in kwargs["subject"]
        assert token in kwargs["html_content"]
        assert token in kwargs["text_content"]
        assert f"{settings.FRONTEND_URL}/reset-password?token={token}" in kwargs["html_content"]


@pytest.fixture
async def registered_user(async_client: AsyncClient):
    payload = {
        "email": "testemailuser@example.com",
        "username": "testemailuser",
        "password": "InitialPassword123!",
        "display_name": "Test Email User",
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return payload


@pytest.mark.asyncio
async def test_forgot_password_endpoint_triggers_email(
    async_client: AsyncClient,
    registered_user: dict,
):
    with patch("app.auth.router.send_password_reset_otp_email", new_callable=AsyncMock) as mock_reset_email:
        mock_reset_email.return_value = True

        response = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": registered_user["email"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "verification instructions have been generated" in data["message"]
        assert data["reset_token"] is not None
        assert len(data["reset_token"]) == 6

        # Verify background task invoked send_password_reset_otp_email
        assert mock_reset_email.call_count == 1
        assert mock_reset_email.call_args.args[0] == registered_user["email"]
        assert mock_reset_email.call_args.args[1] == data["reset_token"]
