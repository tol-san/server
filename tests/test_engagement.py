import uuid
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
async def test_like_and_unlike_post(async_client: AsyncClient):
    author = await create_user(async_client, "likeauthor", "likeauthor@example.com")
    user1 = await create_user(async_client, "likeuser1", "likeuser1@example.com")
    user2 = await create_user(async_client, "likeuser2", "likeuser2@example.com")

    # Create a post
    post_resp = await async_client.post(
        "/api/v1/posts",
        headers=author["headers"],
        json={"post_type": "text", "title": "Cool Post", "content": "Like me!"},
    )
    assert post_resp.status_code == 201
    post_id = post_resp.json()["id"]
    assert post_resp.json()["like_count"] == 0

    # 1. User1 likes the post
    like1_resp = await async_client.post(
        f"/api/v1/posts/{post_id}/like",
        headers=user1["headers"],
    )
    assert like1_resp.status_code == 200
    data1 = like1_resp.json()
    assert data1["liked"] is True
    assert data1["like_count"] == 1

    # Verify via get_post
    get_post_resp = await async_client.get(f"/api/v1/posts/{post_id}")
    assert get_post_resp.json()["like_count"] == 1

    # 2. User1 likes again (idempotent test)
    dup_like_resp = await async_client.post(
        f"/api/v1/posts/{post_id}/like",
        headers=user1["headers"],
    )
    assert dup_like_resp.status_code == 200
    assert dup_like_resp.json()["liked"] is True
    assert dup_like_resp.json()["like_count"] == 1

    # 3. User2 likes the post
    like2_resp = await async_client.post(
        f"/api/v1/posts/{post_id}/like",
        headers=user2["headers"],
    )
    assert like2_resp.status_code == 200
    assert like2_resp.json()["like_count"] == 2

    # 4. User1 unlikes the post
    unlike1_resp = await async_client.delete(
        f"/api/v1/posts/{post_id}/like",
        headers=user1["headers"],
    )
    assert unlike1_resp.status_code == 200
    assert unlike1_resp.json()["liked"] is False
    assert unlike1_resp.json()["like_count"] == 1

    # 5. User1 unlikes again (idempotent test)
    dup_unlike_resp = await async_client.delete(
        f"/api/v1/posts/{post_id}/like",
        headers=user1["headers"],
    )
    assert dup_unlike_resp.status_code == 200
    assert dup_unlike_resp.json()["liked"] is False
    assert dup_unlike_resp.json()["like_count"] == 1

    # 6. User2 unlikes the post -> like_count becomes 0
    unlike2_resp = await async_client.delete(
        f"/api/v1/posts/{post_id}/like",
        headers=user2["headers"],
    )
    assert unlike2_resp.status_code == 200
    assert unlike2_resp.json()["like_count"] == 0


@pytest.mark.asyncio
async def test_save_and_unsave_post_and_list(async_client: AsyncClient):
    author = await create_user(async_client, "saveauthor", "saveauthor@example.com")
    user = await create_user(async_client, "saveuser", "saveuser@example.com")

    # Create two posts
    post1_resp = await async_client.post(
        "/api/v1/posts",
        headers=author["headers"],
        json={"post_type": "text", "title": "First Bookmarked Post", "content": "Important info"},
    )
    post1_id = post1_resp.json()["id"]

    post2_resp = await async_client.post(
        "/api/v1/posts",
        headers=author["headers"],
        json={"post_type": "text", "title": "Second Bookmarked Post", "content": "More info"},
    )
    post2_id = post2_resp.json()["id"]

    # 1. Initially saved posts is empty
    list_saved_0 = await async_client.get(
        "/api/v1/saved-posts",
        headers=user["headers"],
    )
    assert list_saved_0.status_code == 200
    assert list_saved_0.json()["total"] == 0
    assert list_saved_0.json()["items"] == []

    # 2. Save post 1
    save1_resp = await async_client.post(
        f"/api/v1/posts/{post1_id}/save",
        headers=user["headers"],
    )
    assert save1_resp.status_code == 200
    assert save1_resp.json()["saved"] is True
    assert save1_resp.json()["save_count"] == 1

    # 3. Save post 1 again (idempotent)
    dup_save_resp = await async_client.post(
        f"/api/v1/posts/{post1_id}/save",
        headers=user["headers"],
    )
    assert dup_save_resp.status_code == 200
    assert dup_save_resp.json()["save_count"] == 1

    # 4. Save post 2
    save2_resp = await async_client.post(
        f"/api/v1/posts/{post2_id}/save",
        headers=user["headers"],
    )
    assert save2_resp.status_code == 200
    assert save2_resp.json()["save_count"] == 1

    # 5. List saved posts -> should have 2 posts
    list_saved = await async_client.get(
        "/api/v1/saved-posts",
        headers=user["headers"],
    )
    assert list_saved.status_code == 200
    data = list_saved.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    saved_ids = [item["id"] for item in data["items"]]
    assert post1_id in saved_ids
    assert post2_id in saved_ids

    # 6. Test pagination on saved posts
    paginated_resp = await async_client.get(
        "/api/v1/saved-posts?limit=1&offset=0",
        headers=user["headers"],
    )
    assert paginated_resp.status_code == 200
    assert paginated_resp.json()["total"] == 2
    assert len(paginated_resp.json()["items"]) == 1

    # 7. Unsave post 1
    unsave1_resp = await async_client.delete(
        f"/api/v1/posts/{post1_id}/save",
        headers=user["headers"],
    )
    assert unsave1_resp.status_code == 200
    assert unsave1_resp.json()["saved"] is False
    assert unsave1_resp.json()["save_count"] == 0

    # 8. List saved posts -> only post 2 remaining
    list_after_unsave = await async_client.get(
        "/api/v1/saved-posts",
        headers=user["headers"],
    )
    assert list_after_unsave.status_code == 200
    assert list_after_unsave.json()["total"] == 1
    assert list_after_unsave.json()["items"][0]["id"] == post2_id


@pytest.mark.asyncio
async def test_share_post_counter(async_client: AsyncClient):
    author = await create_user(async_client, "shareauthor", "shareauthor@example.com")
    user = await create_user(async_client, "shareuser", "shareuser@example.com")

    post_resp = await async_client.post(
        "/api/v1/posts",
        headers=author["headers"],
        json={"post_type": "text", "title": "Viral Post", "content": "Share this with your friends"},
    )
    post_id = post_resp.json()["id"]
    assert post_resp.json()["share_count"] == 0

    # 1. Share once
    share1_resp = await async_client.post(
        f"/api/v1/posts/{post_id}/share",
        headers=user["headers"],
    )
    assert share1_resp.status_code == 200
    data1 = share1_resp.json()
    assert data1["post_id"] == post_id
    assert data1["share_count"] == 1
    assert data1["share_url"] == f"/posts/{post_id}"

    # 2. Share second time
    share2_resp = await async_client.post(
        f"/api/v1/posts/{post_id}/share",
        headers=user["headers"],
    )
    assert share2_resp.status_code == 200
    assert share2_resp.json()["share_count"] == 2

    # Verify via get_post
    get_post_resp = await async_client.get(f"/api/v1/posts/{post_id}")
    assert get_post_resp.json()["share_count"] == 2


@pytest.mark.asyncio
async def test_engagement_nonexistent_post_404(async_client: AsyncClient):
    user = await create_user(async_client, "notfounduser", "notfounduser@example.com")
    fake_id = uuid.uuid4()

    like_resp = await async_client.post(f"/api/v1/posts/{fake_id}/like", headers=user["headers"])
    assert like_resp.status_code == 404

    unlike_resp = await async_client.delete(f"/api/v1/posts/{fake_id}/like", headers=user["headers"])
    assert unlike_resp.status_code == 404

    save_resp = await async_client.post(f"/api/v1/posts/{fake_id}/save", headers=user["headers"])
    assert save_resp.status_code == 404

    unsave_resp = await async_client.delete(f"/api/v1/posts/{fake_id}/save", headers=user["headers"])
    assert unsave_resp.status_code == 404

    share_resp = await async_client.post(f"/api/v1/posts/{fake_id}/share", headers=user["headers"])
    assert share_resp.status_code == 404
