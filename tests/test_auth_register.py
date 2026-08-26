import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user_success(async_client: AsyncClient):
    payload = {
        "email": "johndoe@example.com",
        "username": "johndoe",
        "password": "SecurePassword123!",
        "display_name": "John Doe",
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert data["email"] == "johndoe@example.com"
    assert data["username"] == "johndoe"
    assert data["is_active"] is True
    assert "password" not in data
    assert "hashed_password" not in data

    # Verify associated profile
    assert data["profile"] is not None
    assert data["profile"]["display_name"] == "John Doe"
    assert data["profile"]["follower_count"] == 0
    assert data["profile"]["following_count"] == 0
    assert data["profile"]["post_count"] == 0


@pytest.mark.asyncio
async def test_register_user_default_display_name(async_client: AsyncClient):
    payload = {
        "email": "janedoe@example.com",
        "username": "janedoe",
        "password": "SecurePassword123!",
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["profile"] is not None
    assert data["profile"]["display_name"] == "janedoe"


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client: AsyncClient):
    payload = {
        "email": "duplicate@example.com",
        "username": "user1",
        "password": "SecurePassword123!",
    }
    # First registration
    response1 = await async_client.post("/api/v1/auth/register", json=payload)
    assert response1.status_code == 201

    # Second registration with same email but different username
    payload2 = {
        "email": "DUPLICATE@EXAMPLE.COM",  # Case insensitive test
        "username": "user2",
        "password": "SecurePassword123!",
    }
    response2 = await async_client.post("/api/v1/auth/register", json=payload2)
    assert response2.status_code == 409
    data = response2.json()
    assert data["error_code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_register_duplicate_username(async_client: AsyncClient):
    payload1 = {
        "email": "unique1@example.com",
        "username": "samename",
        "password": "SecurePassword123!",
    }
    response1 = await async_client.post("/api/v1/auth/register", json=payload1)
    assert response1.status_code == 201

    payload2 = {
        "email": "unique2@example.com",
        "username": "samename",
        "password": "SecurePassword123!",
    }
    response2 = await async_client.post("/api/v1/auth/register", json=payload2)
    assert response2.status_code == 409
    data = response2.json()
    assert data["error_code"] == "USERNAME_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_register_invalid_email_format(async_client: AsyncClient):
    payload = {
        "email": "invalid-email-address",
        "username": "validuser",
        "password": "SecurePassword123!",
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password(async_client: AsyncClient):
    payload = {
        "email": "shortpwd@example.com",
        "username": "shortpwduser",
        "password": "123",  # Less than 8 chars
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_username_characters(async_client: AsyncClient):
    payload = {
        "email": "invaliduser@example.com",
        "username": "invalid user with spaces!",
        "password": "SecurePassword123!",
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_short_username(async_client: AsyncClient):
    payload = {
        "email": "shortname@example.com",
        "username": "ab",  # Less than 3 chars
        "password": "SecurePassword123!",
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
