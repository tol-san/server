import pytest
from httpx import AsyncClient
from app.core.cache import cache_service


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

    return {"id": user_id, "username": username, "headers": headers}


@pytest.mark.asyncio
async def test_cache_service_primitives():
    # 1. Test set and get
    await cache_service.set("test:primitive:key", {"status": "ok", "value": 42}, ttl=60)
    val = await cache_service.get("test:primitive:key")
    assert val is not None
    assert val["value"] == 42

    # 2. Test atomic incr
    new_count = await cache_service.incr("test:primitive:counter", 5)
    assert new_count >= 5

    # 3. Test delete
    await cache_service.delete("test:primitive:key")
    assert await cache_service.get("test:primitive:key") is None

    # 4. Test pattern delete
    await cache_service.set("test:prefix:a", "val_a", ttl=60)
    await cache_service.set("test:prefix:b", "val_b", ttl=60)
    deleted = await cache_service.delete_pattern("test:prefix:*")
    assert deleted >= 2
    assert await cache_service.get("test:prefix:a") is None


@pytest.mark.asyncio
async def test_feed_and_recommendations_caching(async_client: AsyncClient):
    alice = await create_user(async_client, "cache_alice", "cache_alice@example.com")

    # 1. Discover feed caching
    resp1 = await async_client.get("/api/v1/feeds/discover", headers=alice["headers"])
    assert resp1.status_code == 200

    # Repeat request — must return same data (cache hit)
    resp2 = await async_client.get("/api/v1/feeds/discover", headers=alice["headers"])
    assert resp2.status_code == 200
    assert resp2.json()["total"] == resp1.json()["total"]
    assert resp2.json()["items"] == resp1.json()["items"]

    # 2. Recommendations caching
    rec_resp1 = await async_client.get("/api/v1/recommendations/communities", headers=alice["headers"])
    assert rec_resp1.status_code == 200

    cached_rec = await cache_service.get(f"cache:rec:comm:{alice['id']}:10:0")
    assert cached_rec is not None


@pytest.mark.asyncio
async def test_atomic_share_counter_and_unread_cache(async_client: AsyncClient):
    user = await create_user(async_client, "cache_counter_user", "counter@example.com")
    actor = await create_user(async_client, "cache_actor_user", "actor@example.com")

    # 1. Create post and test share counter increment
    post_resp = await async_client.post(
        "/api/v1/posts",
        headers=user["headers"],
        json={"post_type": "text", "title": "Viral Post", "content": "Share this!"},
    )
    post_id = post_resp.json()["id"]

    share_resp = await async_client.post(f"/api/v1/posts/{post_id}/share", headers=user["headers"])
    assert share_resp.status_code == 200
    assert share_resp.json()["share_count"] == 1

    # 2. Notifications unread count cache
    unread_resp = await async_client.get("/api/v1/notifications/unread-count", headers=user["headers"])
    assert unread_resp.status_code == 200
    assert unread_resp.json()["unread_count"] == 0

    cached_unread = await cache_service.get(f"cache:notif:unread:{user['id']}")
    assert cached_unread == 0

    # Actor follows user -> invalidates unread cache and generates notification
    await async_client.post(f"/api/v1/users/{user['id']}/follow", headers=actor["headers"])

    # Query unread count again -> gets updated count
    unread_resp2 = await async_client.get("/api/v1/notifications/unread-count", headers=user["headers"])
    assert unread_resp2.status_code == 200
    assert unread_resp2.json()["unread_count"] >= 1
