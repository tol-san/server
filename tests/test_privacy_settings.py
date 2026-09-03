import pytest
from httpx import AsyncClient


async def create_user(async_client: AsyncClient, username: str, email: str):
    payload = {
        "email": email,
        "username": username,
        "password": "Password123!",
        "display_name": f"User {username}",
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=payload)
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return {"id": user_id, "username": username, "token": token, "headers": headers}


@pytest.mark.asyncio
async def test_get_privacy_settings_defaults(async_client: AsyncClient):
    user = await create_user(async_client, "priv_user1", "priv1@example.com")

    resp = await async_client.get("/api/v1/users/me/privacy", headers=user["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_private"] is False
    assert data["allow_comments"] == "everyone"
    assert data["allow_mentions"] == "everyone"
    assert data["show_activity_status"] is True
    assert data["search_discoverable"] is True


@pytest.mark.asyncio
async def test_patch_privacy_settings(async_client: AsyncClient):
    user = await create_user(async_client, "priv_user2", "priv2@example.com")

    patch_payload = {
        "is_private": True,
        "allow_comments": "following",
        "show_activity_status": False,
        "search_discoverable": False,
    }
    patch_resp = await async_client.patch(
        "/api/v1/users/me/privacy",
        headers=user["headers"],
        json=patch_payload,
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["is_private"] is True
    assert data["allow_comments"] == "following"
    assert data["allow_mentions"] == "everyone"  # unchanged
    assert data["show_activity_status"] is False
    assert data["search_discoverable"] is False

    # Verify persistence on subsequent GET
    get_resp = await async_client.get("/api/v1/users/me/privacy", headers=user["headers"])
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["is_private"] is True
    assert get_data["show_activity_status"] is False


@pytest.mark.asyncio
async def test_privacy_settings_unauthorized(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/users/me/privacy")
    assert resp.status_code == 401
