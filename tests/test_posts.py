import io
import pytest
from httpx import AsyncClient
from PIL import Image


def create_test_image_bytes(format_name: str = "PNG", size: tuple[int, int] = (400, 400)) -> bytes:
    img = Image.new("RGB", size, color=(220, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format=format_name)
    return buf.getvalue()


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
async def test_create_multi_format_personal_posts(async_client: AsyncClient):
    user = await create_user(async_client, "postcreator1", "postcreator1@example.com")

    # 1. Text Post
    text_payload = {
        "post_type": "text",
        "title": "My First Blog Post",
        "content": "Exploring modern FastAPI + Flutter architecture.",
        "visibility": "public",
    }
    text_resp = await async_client.post(
        "/api/v1/posts",
        headers=user["headers"],
        json=text_payload,
    )
    assert text_resp.status_code == 201
    text_data = text_resp.json()
    assert text_data["title"] == "My First Blog Post"
    assert text_data["post_type"] == "text"
    assert text_data["author"]["username"] == "postcreator1"
    assert text_data["community"] is None

    # 2. Multi-Image Post
    img_payload = {
        "post_type": "image",
        "content": "Sunset vibes at the beach",
        "visibility": "public",
        "media": [
            {"media_type": "image", "url": f"http://storage.test/genz-media-private/posts/{user['id']}/images/img1.webp?signature=test", "width": 1080, "height": 1080, "order": 0},
            {"media_type": "image", "url": f"http://storage.test/genz-media-private/posts/{user['id']}/images/img2.webp?signature=test", "width": 1080, "height": 1080, "order": 1},
        ],
    }
    img_resp = await async_client.post(
        "/api/v1/posts",
        headers=user["headers"],
        json=img_payload,
    )
    assert img_resp.status_code == 201
    img_data = img_resp.json()
    assert img_data["post_type"] == "image"
    assert len(img_data["media"]) == 2
    assert f"posts/{user['id']}/images/img1.webp" in img_data["media"][0]["url"]

    # 3. Short Video Post
    video_payload = {
        "post_type": "video",
        "content": "Quick flutter animation demo",
        "visibility": "public",
        "media": [
            {
                "media_type": "video",
                "url": f"http://storage.test/genz-media-private/posts/{user['id']}/videos/video1.mp4?signature=test",
                "thumbnail_url": f"http://storage.test/genz-media-private/posts/{user['id']}/images/thumb1.webp?signature=test",
                "duration": 18.5,
                "order": 0,
            }
        ],
    }
    vid_resp = await async_client.post(
        "/api/v1/posts",
        headers=user["headers"],
        json=video_payload,
    )
    assert vid_resp.status_code == 201
    vid_data = vid_resp.json()
    assert vid_data["post_type"] == "video"
    assert len(vid_data["media"]) == 1
    assert vid_data["media"][0]["duration"] == 18.5


@pytest.mark.asyncio
async def test_community_post_membership_rules(async_client: AsyncClient):
    owner = await create_user(async_client, "commownerpost", "commownerpost@example.com")
    member = await create_user(async_client, "commmemberpost", "commmemberpost@example.com")
    non_member = await create_user(async_client, "nonmemberpost", "nonmemberpost@example.com")

    # Create community
    comm_resp = await async_client.post(
        "/api/v1/communities",
        headers=owner["headers"],
        json={"name": "Gaming Lounge", "is_private": False},
    )
    comm_id = comm_resp.json()["id"]

    # Member joins
    await async_client.post(f"/api/v1/communities/{comm_id}/join", headers=member["headers"])

    # 1. Non-member attempts to post -> 403 Forbidden
    fail_post = await async_client.post(
        "/api/v1/posts",
        headers=non_member["headers"],
        json={
            "post_type": "text",
            "title": "Spam",
            "content": "Unauthorized post",
            "community_id": comm_id,
        },
    )
    assert fail_post.status_code == 403

    # 2. Member posts to community -> 201 Created
    member_post = await async_client.post(
        "/api/v1/posts",
        headers=member["headers"],
        json={
            "post_type": "text",
            "title": "GG Everyone",
            "content": "Great matches tonight!",
            "community_id": comm_id,
        },
    )
    assert member_post.status_code == 201
    post_data = member_post.json()
    assert post_data["community"]["id"] == comm_id
    assert post_data["community"]["name"] == "Gaming Lounge"


@pytest.mark.asyncio
async def test_media_upload_endpoint(async_client: AsyncClient):
    user = await create_user(async_client, "mediauser", "mediauser@example.com")

    # 1. Image upload
    image_bytes = create_test_image_bytes("PNG", (600, 600))
    img_files = {"file": ("photo.png", io.BytesIO(image_bytes), "image/png")}
    img_upload = await async_client.post(
        "/api/v1/posts/media",
        headers=user["headers"],
        files=img_files,
    )
    assert img_upload.status_code == 200
    img_resp_data = img_upload.json()
    assert img_resp_data["media_type"] == "image"
    assert img_resp_data["url"].split("?", 1)[0].endswith(".webp")
    assert img_resp_data["width"] == 600
    assert img_resp_data["height"] == 600

    # 2. Video upload
    dummy_video_bytes = b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2mp41" + b"\x00" * 100
    vid_files = {"file": ("clip.mp4", io.BytesIO(dummy_video_bytes), "video/mp4")}
    vid_upload = await async_client.post(
        "/api/v1/posts/media",
        headers=user["headers"],
        files=vid_files,
    )
    assert vid_upload.status_code == 200
    vid_resp_data = vid_upload.json()
    assert vid_resp_data["media_type"] == "video"
    assert vid_resp_data["url"].split("?", 1)[0].endswith(".mp4")


@pytest.mark.asyncio
async def test_get_and_list_posts(async_client: AsyncClient):
    author = await create_user(async_client, "feedauthor", "feedauthor@example.com")

    # Create post
    post_resp = await async_client.post(
        "/api/v1/posts",
        headers=author["headers"],
        json={"post_type": "text", "title": "Feed Test Post", "content": "Searchable keywords hello"},
    )
    post_id = post_resp.json()["id"]

    # 1. Get single post
    get_resp = await async_client.get(f"/api/v1/posts/{post_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Feed Test Post"

    # 2. Search posts
    search_resp = await async_client.get("/api/v1/posts?search=keywords")
    assert search_resp.status_code == 200
    assert search_resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_post_deletion_permissions(async_client: AsyncClient):
    comm_owner = await create_user(async_client, "postdelcommowner", "postdelcommowner@example.com")
    member = await create_user(async_client, "postdelmember", "postdelmember@example.com")
    random_user = await create_user(async_client, "postdelother", "postdelother@example.com")

    # Create community
    comm_resp = await async_client.post(
        "/api/v1/communities",
        headers=comm_owner["headers"],
        json={"name": "Moderated Community"},
    )
    comm_id = comm_resp.json()["id"]

    # Member joins and creates post
    await async_client.post(f"/api/v1/communities/{comm_id}/join", headers=member["headers"])
    post_resp = await async_client.post(
        "/api/v1/posts",
        headers=member["headers"],
        json={"post_type": "text", "content": "Off-topic comment", "community_id": comm_id},
    )
    post_id = post_resp.json()["id"]

    # 1. Random user cannot delete member's post -> 403
    fail_del = await async_client.delete(f"/api/v1/posts/{post_id}", headers=random_user["headers"])
    assert fail_del.status_code == 403

    # 2. Community Owner can delete post in their community -> 200 OK
    comm_owner_del = await async_client.delete(f"/api/v1/posts/{post_id}", headers=comm_owner["headers"])
    assert comm_owner_del.status_code == 200

    # Confirm post is gone -> 404
    get_after = await async_client.get(f"/api/v1/posts/{post_id}")
    assert get_after.status_code == 404


@pytest.mark.asyncio
async def test_post_visibility_is_consistent_across_derived_endpoints(
    async_client: AsyncClient,
):
    author = await create_user(async_client, "privacyauthor", "privacyauthor@example.com")
    viewer = await create_user(async_client, "privacyviewer", "privacyviewer@example.com")
    unique_text = "visibility-policy-sentinel"
    created = await async_client.post(
        "/api/v1/posts",
        headers=author["headers"],
        json={
            "post_type": "text",
            "content": unique_text,
            "visibility": "followers_only",
        },
    )
    post_id = created.json()["id"]

    assert (await async_client.get(f"/api/v1/posts/{post_id}")).status_code == 404
    assert (
        await async_client.get(f"/api/v1/posts/{post_id}/comments")
    ).status_code == 404
    assert (
        await async_client.post(
            f"/api/v1/posts/{post_id}/like", headers=viewer["headers"]
        )
    ).status_code == 404
    hidden_search = await async_client.get(
        f"/api/v1/search/posts?q={unique_text}", headers=viewer["headers"]
    )
    assert hidden_search.json()["total"] == 0

    follow = await async_client.post(
        f"/api/v1/users/{author['id']}/follow", headers=viewer["headers"]
    )
    assert follow.status_code == 200
    visible = await async_client.get(
        f"/api/v1/posts/{post_id}", headers=viewer["headers"]
    )
    assert visible.status_code == 200


@pytest.mark.asyncio
async def test_post_rejects_media_owned_by_another_user(async_client: AsyncClient):
    attacker = await create_user(async_client, "mediaattacker", "mediaattacker@example.com")
    victim = await create_user(async_client, "mediavictim", "mediavictim@example.com")
    response = await async_client.post(
        "/api/v1/posts",
        headers=attacker["headers"],
        json={
            "post_type": "image",
            "media": [
                {
                    "media_type": "image",
                    "url": f"http://storage.test/genz-media-private/posts/{victim['id']}/images/private.webp?signature=test",
                }
            ],
        },
    )
    assert response.status_code == 400
