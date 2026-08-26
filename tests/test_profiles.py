import pytest
from httpx import AsyncClient


@pytest.fixture
async def authenticated_user(async_client: AsyncClient):
    # 1. Register
    reg_payload = {
        "email": "profileuser@example.com",
        "username": "profileuser",
        "password": "Password123!",
        "display_name": "Original Name",
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201

    # 2. Login
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": reg_payload["email"], "password": reg_payload["password"]},
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    return {"user": reg_payload, "token": access_token, "headers": headers}


@pytest.mark.asyncio
async def test_get_public_profile_success(async_client: AsyncClient, authenticated_user: dict):
    username = authenticated_user["user"]["username"]
    response = await async_client.get(f"/api/v1/users/{username}")
    assert response.status_code == 200
    data = response.json()

    assert data["username"] == username
    assert data["display_name"] == "Original Name"
    assert data["follower_count"] == 0
    assert data["following_count"] == 0
    assert data["post_count"] == 0
    assert "email" not in data
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_get_public_profile_not_found(async_client: AsyncClient):
    response = await async_client.get("/api/v1/users/nonexistentuser")
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_my_profile_authenticated(async_client: AsyncClient, authenticated_user: dict):
    response = await async_client.get("/api/v1/profiles/me", headers=authenticated_user["headers"])
    assert response.status_code == 200
    data = response.json()

    assert data["email"] == authenticated_user["user"]["email"]
    assert data["username"] == authenticated_user["user"]["username"]
    assert data["display_name"] == "Original Name"
    assert data["is_active"] is True
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_get_my_profile_unauthenticated(async_client: AsyncClient):
    response = await async_client.get("/api/v1/profiles/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_display_name_and_bio(async_client: AsyncClient, authenticated_user: dict):
    update_payload = {
        "display_name": "Updated Display Name",
        "bio": "Passionate developer building GenZ Media.",
    }
    patch_resp = await async_client.patch(
        "/api/v1/profiles/me",
        headers=authenticated_user["headers"],
        json=update_payload,
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["display_name"] == "Updated Display Name"
    assert data["bio"] == "Passionate developer building GenZ Media."

    # Verify public profile reflects changes
    username = authenticated_user["user"]["username"]
    pub_resp = await async_client.get(f"/api/v1/users/{username}")
    assert pub_resp.status_code == 200
    assert pub_resp.json()["display_name"] == "Updated Display Name"
    assert pub_resp.json()["bio"] == "Passionate developer building GenZ Media."


@pytest.mark.asyncio
async def test_update_avatar_url(async_client: AsyncClient, authenticated_user: dict):
    avatar_url = "https://images.example.com/avatar/user123.jpg"
    patch_resp = await async_client.patch(
        "/api/v1/profiles/me",
        headers=authenticated_user["headers"],
        json={"avatar_url": avatar_url},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["avatar_url"] == avatar_url


@pytest.mark.asyncio
async def test_partial_update_preserves_other_fields(async_client: AsyncClient, authenticated_user: dict):
    headers = authenticated_user["headers"]

    # First update: set bio and avatar
    await async_client.patch(
        "/api/v1/profiles/me",
        headers=headers,
        json={"bio": "Initial bio", "avatar_url": "https://example.com/avatar.png"},
    )

    # Second update: change only display_name
    patch_resp = await async_client.patch(
        "/api/v1/profiles/me",
        headers=headers,
        json={"display_name": "Brand New Name"},
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["display_name"] == "Brand New Name"
    assert data["bio"] == "Initial bio"
    assert data["avatar_url"] == "https://example.com/avatar.png"


@pytest.mark.asyncio
async def test_update_bio_too_long(async_client: AsyncClient, authenticated_user: dict):
    long_bio = "a" * 501
    patch_resp = await async_client.patch(
        "/api/v1/profiles/me",
        headers=authenticated_user["headers"],
        json={"bio": long_bio},
    )
    assert patch_resp.status_code == 422


@pytest.mark.asyncio
async def test_update_profile_unauthenticated(async_client: AsyncClient):
    patch_resp = await async_client.patch(
        "/api/v1/profiles/me",
        json={"display_name": "Unauthenticated Update"},
    )
    assert patch_resp.status_code == 401
