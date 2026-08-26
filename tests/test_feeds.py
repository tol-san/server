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

    return {"id": user_id, "username": username, "headers": headers}


@pytest.mark.asyncio
async def test_home_feed_sources_and_exclusions(async_client: AsyncClient):
    user = await create_user(async_client, "feedmainuser", "feedmainuser@example.com")
    followed_user = await create_user(async_client, "feedfollowed", "feedfollowed@example.com")
    stranger = await create_user(async_client, "feedstranger", "feedstranger@example.com")
    blocked_user = await create_user(async_client, "feedblocked", "feedblocked@example.com")

    # 1. Main user follows followed_user
    await async_client.post(f"/api/v1/users/{followed_user['id']}/follow", headers=user["headers"])

    # 2. Main user blocks blocked_user
    await async_client.post(f"/api/v1/users/{blocked_user['id']}/block", headers=user["headers"])

    # 3. Create community and join
    comm_resp = await async_client.post(
        "/api/v1/communities",
        headers=followed_user["headers"],
        json={"name": "Gaming Feed Community"},
    )
    comm_id = comm_resp.json()["id"]
    await async_client.post(f"/api/v1/communities/{comm_id}/join", headers=user["headers"])

    # 4. Create various posts:
    # Post A: By followed user (personal public) -> SHOULD appear
    p_a = await async_client.post(
        "/api/v1/posts",
        headers=followed_user["headers"],
        json={"post_type": "text", "title": "Post from followed user", "visibility": "public"},
    )
    p_a_id = p_a.json()["id"]

    # Post B: By stranger in joined community -> SHOULD appear
    # Let stranger join community first
    await async_client.post(f"/api/v1/communities/{comm_id}/join", headers=stranger["headers"])
    p_b = await async_client.post(
        "/api/v1/posts",
        headers=stranger["headers"],
        json={"post_type": "text", "title": "Community post by stranger", "community_id": comm_id},
    )
    p_b_id = p_b.json()["id"]

    # Post C: By stranger on their own personal profile -> SHOULD NOT appear
    p_c = await async_client.post(
        "/api/v1/posts",
        headers=stranger["headers"],
        json={"post_type": "text", "title": "Personal stranger post", "visibility": "public"},
    )
    p_c_id = p_c.json()["id"]

    # Post D: By blocked user in joined community -> SHOULD NOT appear
    await async_client.post(f"/api/v1/communities/{comm_id}/join", headers=blocked_user["headers"])
    p_d = await async_client.post(
        "/api/v1/posts",
        headers=blocked_user["headers"],
        json={"post_type": "text", "title": "Blocked user post", "community_id": comm_id},
    )
    p_d_id = p_d.json()["id"]

    # Post E: By main user themselves -> SHOULD appear
    p_e = await async_client.post(
        "/api/v1/posts",
        headers=user["headers"],
        json={"post_type": "text", "title": "My own post", "visibility": "public"},
    )
    p_e_id = p_e.json()["id"]

    # Query Home Feed
    feed_resp = await async_client.get("/api/v1/feeds/home", headers=user["headers"])
    assert feed_resp.status_code == 200
    feed_data = feed_resp.json()
    post_ids = [item["id"] for item in feed_data["items"]]

    assert p_a_id in post_ids
    assert p_b_id in post_ids
    assert p_e_id in post_ids
    assert p_c_id not in post_ids
    assert p_d_id not in post_ids


@pytest.mark.asyncio
async def test_discover_feed_ranking(async_client: AsyncClient):
    creator = await create_user(async_client, "discovercreator", "discovercreator@example.com")
    viewer = await create_user(async_client, "discoverviewer", "discoverviewer@example.com")

    # Create two posts
    post1_resp = await async_client.post(
        "/api/v1/posts",
        headers=creator["headers"],
        json={"post_type": "text", "title": "Low Engagement Post", "content": "Just a thought"},
    )
    post1_id = post1_resp.json()["id"]

    post2_resp = await async_client.post(
        "/api/v1/posts",
        headers=creator["headers"],
        json={"post_type": "text", "title": "High Engagement Post", "content": "Viral content"},
    )
    post2_id = post2_resp.json()["id"]

    # Boost post2 with likes and shares
    await async_client.post(f"/api/v1/posts/{post2_id}/like", headers=viewer["headers"])
    await async_client.post(f"/api/v1/posts/{post2_id}/save", headers=viewer["headers"])
    await async_client.post(f"/api/v1/posts/{post2_id}/share", headers=viewer["headers"])

    # Query Discover Feed
    discover_resp = await async_client.get("/api/v1/feeds/discover", headers=viewer["headers"])
    assert discover_resp.status_code == 200
    items = discover_resp.json()["items"]
    assert len(items) >= 2

    # High engagement post should be ranked before low engagement post
    found_post1_idx = None
    found_post2_idx = None
    for idx, p in enumerate(items):
        if p["id"] == post1_id:
            found_post1_idx = idx
        elif p["id"] == post2_id:
            found_post2_idx = idx

    assert found_post2_idx is not None
    assert found_post1_idx is not None
    assert found_post2_idx < found_post1_idx


@pytest.mark.asyncio
async def test_shorts_feed_filtering(async_client: AsyncClient):
    creator = await create_user(async_client, "shortscreator", "shortscreator@example.com")
    viewer = await create_user(async_client, "shortsviewer", "shortsviewer@example.com")

    # 1. Create text post
    text_post = await async_client.post(
        "/api/v1/posts",
        headers=creator["headers"],
        json={"post_type": "text", "title": "Not a video"},
    )
    text_post_id = text_post.json()["id"]

    # 2. Create short video post
    video_post = await async_client.post(
        "/api/v1/posts",
        headers=creator["headers"],
        json={
            "post_type": "video",
            "content": "Awesome trick shot",
            "media": [
                {
                    "media_type": "video",
                    "url": "https://example.com/trickshot.mp4",
                    "duration": 12.0,
                }
            ],
        },
    )
    assert video_post.status_code == 201
    video_post_id = video_post.json()["id"]

    # Query Shorts Feed
    shorts_resp = await async_client.get("/api/v1/feeds/shorts", headers=viewer["headers"])
    assert shorts_resp.status_code == 200
    shorts_data = shorts_resp.json()
    shorts_ids = [item["id"] for item in shorts_data["items"]]

    assert video_post_id in shorts_ids
    assert text_post_id not in shorts_ids
    for item in shorts_data["items"]:
        assert item["post_type"] == "video"
