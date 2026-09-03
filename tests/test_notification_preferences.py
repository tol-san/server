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
async def test_get_notification_preferences_defaults(async_client: AsyncClient):
    user = await create_user(async_client, "pref_user1", "pref1@example.com")

    resp = await async_client.get("/api/v1/notifications/preferences", headers=user["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["likes_enabled"] is True
    assert data["comments_enabled"] is True
    assert data["follows_enabled"] is True
    assert data["mentions_enabled"] is True
    assert data["community_enabled"] is True
    assert data["email_enabled"] is False
    assert data["push_enabled"] is True
    assert data["quiet_hours_enabled"] is False


@pytest.mark.asyncio
async def test_patch_notification_preferences(async_client: AsyncClient):
    user = await create_user(async_client, "pref_user2", "pref2@example.com")

    patch_payload = {
        "likes_enabled": False,
        "push_enabled": False,
        "quiet_hours_enabled": True,
        "quiet_hours_start": "23:00",
        "quiet_hours_end": "08:00",
    }
    patch_resp = await async_client.patch(
        "/api/v1/notifications/preferences",
        headers=user["headers"],
        json=patch_payload,
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["likes_enabled"] is False
    assert data["comments_enabled"] is True  # preserved
    assert data["push_enabled"] is False
    assert data["quiet_hours_enabled"] is True
    assert data["quiet_hours_start"] == "23:00"
    assert data["quiet_hours_end"] == "08:00"


@pytest.mark.asyncio
async def test_notification_suppression_when_disabled(async_client: AsyncClient):
    alice = await create_user(async_client, "pref_alice", "pref_alice@example.com")
    bob = await create_user(async_client, "pref_bob", "pref_bob@example.com")

    # Alice disables follow notifications
    patch_resp = await async_client.patch(
        "/api/v1/notifications/preferences",
        headers=alice["headers"],
        json={"follows_enabled": False},
    )
    assert patch_resp.status_code == 200

    # Bob follows Alice
    follow_resp = await async_client.post(f"/api/v1/users/{alice['id']}/follow", headers=bob["headers"])
    assert follow_resp.status_code == 200

    # Alice checks notifications - should have 0 notifications
    alice_notifs = await async_client.get("/api/v1/notifications", headers=alice["headers"])
    assert alice_notifs.status_code == 200
    assert len(alice_notifs.json()["items"]) == 0

    # Alice enables follow notifications
    await async_client.patch(
        "/api/v1/notifications/preferences",
        headers=alice["headers"],
        json={"follows_enabled": True},
    )

    # Bob unfollows and re-follows Alice
    await async_client.delete(f"/api/v1/users/{alice['id']}/follow", headers=bob["headers"])
    await async_client.post(f"/api/v1/users/{alice['id']}/follow", headers=bob["headers"])

    # Alice should now receive the new_follower notification
    alice_notifs2 = await async_client.get("/api/v1/notifications", headers=alice["headers"])
    assert alice_notifs2.status_code == 200
    items = alice_notifs2.json()["items"]
    assert len(items) == 1
    assert items[0]["notification_type"] == "new_follower"
