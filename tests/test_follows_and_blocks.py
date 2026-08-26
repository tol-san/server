import pytest
from httpx import AsyncClient


async def create_user_and_login(async_client: AsyncClient, username: str, email: str):
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

    return {"id": user_id, "username": username, "headers": headers}


@pytest.mark.asyncio
async def test_follow_and_unfollow_lifecycle(async_client: AsyncClient):
    user_a = await create_user_and_login(async_client, "usera", "usera@example.com")
    user_b = await create_user_and_login(async_client, "userb", "userb@example.com")

    # 1. User A follows User B
    follow_resp = await async_client.post(
        f"/api/v1/users/{user_b['id']}/follow",
        headers=user_a["headers"],
    )
    assert follow_resp.status_code == 200
    assert follow_resp.json()["is_following"] is True

    # 2. Check profiles for updated counts
    prof_a = await async_client.get("/api/v1/profiles/me", headers=user_a["headers"])
    assert prof_a.json()["following_count"] == 1
    assert prof_a.json()["follower_count"] == 0

    prof_b = await async_client.get("/api/v1/profiles/me", headers=user_b["headers"])
    assert prof_b.json()["follower_count"] == 1
    assert prof_b.json()["following_count"] == 0

    # 3. User A unfollows User B
    unfollow_resp = await async_client.delete(
        f"/api/v1/users/{user_b['id']}/follow",
        headers=user_a["headers"],
    )
    assert unfollow_resp.status_code == 200
    assert unfollow_resp.json()["is_following"] is False

    # 4. Check profiles after unfollow
    prof_a = await async_client.get("/api/v1/profiles/me", headers=user_a["headers"])
    assert prof_a.json()["following_count"] == 0

    prof_b = await async_client.get("/api/v1/profiles/me", headers=user_b["headers"])
    assert prof_b.json()["follower_count"] == 0


@pytest.mark.asyncio
async def test_cannot_follow_self(async_client: AsyncClient):
    user_a = await create_user_and_login(async_client, "userself", "userself@example.com")
    resp = await async_client.post(
        f"/api/v1/users/{user_a['id']}/follow",
        headers=user_a["headers"],
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_duplicate_follow_is_idempotent(async_client: AsyncClient):
    user_a = await create_user_and_login(async_client, "userdup1", "dup1@example.com")
    user_b = await create_user_and_login(async_client, "userdup2", "dup2@example.com")

    # Follow once
    resp1 = await async_client.post(f"/api/v1/users/{user_b['id']}/follow", headers=user_a["headers"])
    assert resp1.status_code == 200

    # Follow again
    resp2 = await async_client.post(f"/api/v1/users/{user_b['id']}/follow", headers=user_a["headers"])
    assert resp2.status_code == 200

    # Counter should still be 1
    prof_a = await async_client.get("/api/v1/profiles/me", headers=user_a["headers"])
    assert prof_a.json()["following_count"] == 1


@pytest.mark.asyncio
async def test_followers_and_following_lists(async_client: AsyncClient):
    user_x = await create_user_and_login(async_client, "listx", "listx@example.com")
    user_y = await create_user_and_login(async_client, "listy", "listy@example.com")
    user_z = await create_user_and_login(async_client, "listz", "listz@example.com")

    # X and Y follow Z
    await async_client.post(f"/api/v1/users/{user_z['id']}/follow", headers=user_x["headers"])
    await async_client.post(f"/api/v1/users/{user_z['id']}/follow", headers=user_y["headers"])

    # Get Z's followers
    followers_resp = await async_client.get(f"/api/v1/users/{user_z['id']}/followers")
    assert followers_resp.status_code == 200
    data = followers_resp.json()
    assert data["total"] == 2
    usernames = [u["username"] for u in data["items"]]
    assert "listx" in usernames
    assert "listy" in usernames

    # Get X's following
    following_resp = await async_client.get(f"/api/v1/users/{user_x['id']}/following")
    assert following_resp.status_code == 200
    following_data = following_resp.json()
    assert following_data["total"] == 1
    assert following_data["items"][0]["username"] == "listz"


@pytest.mark.asyncio
async def test_relationship_endpoint(async_client: AsyncClient):
    user_a = await create_user_and_login(async_client, "rel_a", "rel_a@example.com")
    user_b = await create_user_and_login(async_client, "rel_b", "rel_b@example.com")

    # A follows B
    await async_client.post(f"/api/v1/users/{user_b['id']}/follow", headers=user_a["headers"])

    # From A's perspective
    rel_a = await async_client.get(f"/api/v1/users/{user_b['id']}/relationship", headers=user_a["headers"])
    assert rel_a.status_code == 200
    data_a = rel_a.json()
    assert data_a["is_following"] is True
    assert data_a["is_followed_by"] is False
    assert data_a["is_blocking"] is False
    assert data_a["is_blocked_by"] is False

    # From B's perspective
    rel_b = await async_client.get(f"/api/v1/users/{user_a['id']}/relationship", headers=user_b["headers"])
    assert rel_b.status_code == 200
    data_b = rel_b.json()
    assert data_b["is_following"] is False
    assert data_b["is_followed_by"] is True


@pytest.mark.asyncio
async def test_block_user_severs_follows_and_prevents_follow(async_client: AsyncClient):
    user_a = await create_user_and_login(async_client, "blocka", "blocka@example.com")
    user_b = await create_user_and_login(async_client, "blockb", "blockb@example.com")

    # Mutual follow: A follows B and B follows A
    await async_client.post(f"/api/v1/users/{user_b['id']}/follow", headers=user_a["headers"])
    await async_client.post(f"/api/v1/users/{user_a['id']}/follow", headers=user_b["headers"])

    # Verify both have count 1
    prof_a = await async_client.get("/api/v1/profiles/me", headers=user_a["headers"])
    assert prof_a.json()["following_count"] == 1
    assert prof_a.json()["follower_count"] == 1

    # User A blocks User B
    block_resp = await async_client.post(
        f"/api/v1/users/{user_b['id']}/block",
        headers=user_a["headers"],
    )
    assert block_resp.status_code == 200
    assert block_resp.json()["is_blocking"] is True

    # Check both follow relations severed and counters = 0
    prof_a_after = await async_client.get("/api/v1/profiles/me", headers=user_a["headers"])
    assert prof_a_after.json()["following_count"] == 0
    assert prof_a_after.json()["follower_count"] == 0

    prof_b_after = await async_client.get("/api/v1/profiles/me", headers=user_b["headers"])
    assert prof_b_after.json()["following_count"] == 0
    assert prof_b_after.json()["follower_count"] == 0

    # User B tries to follow User A while blocked -> 403 Forbidden
    cant_follow = await async_client.post(
        f"/api/v1/users/{user_a['id']}/follow",
        headers=user_b["headers"],
    )
    assert cant_follow.status_code == 403

    # Check blocked list
    blocked_list = await async_client.get("/api/v1/users/me/blocked", headers=user_a["headers"])
    assert blocked_list.status_code == 200
    assert blocked_list.json()["total"] == 1
    assert blocked_list.json()["items"][0]["username"] == "blockb"

    # User A unblocks User B
    unblock_resp = await async_client.delete(
        f"/api/v1/users/{user_b['id']}/block",
        headers=user_a["headers"],
    )
    assert unblock_resp.status_code == 200
    assert unblock_resp.json()["is_blocking"] is False

    # Now B can follow A
    can_follow = await async_client.post(
        f"/api/v1/users/{user_a['id']}/follow",
        headers=user_b["headers"],
    )
    assert can_follow.status_code == 200
