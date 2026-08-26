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
async def test_comments_and_nested_replies(async_client: AsyncClient):
    post_author = await create_user(async_client, "commentpostauthor", "commentpostauthor@example.com")
    commenter = await create_user(async_client, "topcommenter", "topcommenter@example.com")
    replier = await create_user(async_client, "replier", "replier@example.com")

    # 1. Create a post
    post_resp = await async_client.post(
        "/api/v1/posts",
        headers=post_author["headers"],
        json={"post_type": "text", "title": "Discussion Post", "content": "Let's discuss!"},
    )
    post_id = post_resp.json()["id"]

    # 2. Create top-level comment
    c1_resp = await async_client.post(
        f"/api/v1/posts/{post_id}/comments",
        headers=commenter["headers"],
        json={"content": "This is a great point!"},
    )
    assert c1_resp.status_code == 201
    c1_data = c1_resp.json()
    assert c1_data["content"] == "This is a great point!"
    assert c1_data["parent_id"] is None
    assert c1_data["author"]["username"] == "topcommenter"
    c1_id = c1_data["id"]

    # Verify post comment count = 1
    post_detail1 = await async_client.get(f"/api/v1/posts/{post_id}")
    assert post_detail1.json()["comment_count"] == 1

    # 3. Create nested reply
    reply_resp = await async_client.post(
        f"/api/v1/posts/{post_id}/comments",
        headers=replier["headers"],
        json={"content": "I agree with you completely.", "parent_id": c1_id},
    )
    assert reply_resp.status_code == 201
    reply_data = reply_resp.json()
    assert reply_data["parent_id"] == c1_id
    assert reply_data["author"]["username"] == "replier"

    # Verify post comment count = 2
    post_detail2 = await async_client.get(f"/api/v1/posts/{post_id}")
    assert post_detail2.json()["comment_count"] == 2

    # 4. List top-level comments
    list_top = await async_client.get(f"/api/v1/posts/{post_id}/comments")
    assert list_top.status_code == 200
    assert list_top.json()["total"] == 1
    assert list_top.json()["items"][0]["reply_count"] == 1

    # 5. List replies under parent
    list_replies = await async_client.get(f"/api/v1/comments/{c1_id}/replies")
    assert list_replies.status_code == 200
    assert list_replies.json()["total"] == 1
    assert list_replies.json()["items"][0]["content"] == "I agree with you completely."


@pytest.mark.asyncio
async def test_edit_comment_moderation(async_client: AsyncClient):
    author = await create_user(async_client, "editauthor", "editauthor@example.com")
    other = await create_user(async_client, "editother", "editother@example.com")

    post_resp = await async_client.post(
        "/api/v1/posts",
        headers=author["headers"],
        json={"post_type": "text", "content": "Sample post"},
    )
    post_id = post_resp.json()["id"]

    comment_resp = await async_client.post(
        f"/api/v1/posts/{post_id}/comments",
        headers=author["headers"],
        json={"content": "Original comment"},
    )
    comment_id = comment_resp.json()["id"]

    # 1. Author edits comment
    edit_resp = await async_client.patch(
        f"/api/v1/comments/{comment_id}",
        headers=author["headers"],
        json={"content": "Edited comment text"},
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["content"] == "Edited comment text"
    assert edit_resp.json()["is_edited"] is True

    # 2. Non-author cannot edit comment
    fail_edit = await async_client.patch(
        f"/api/v1/comments/{comment_id}",
        headers=other["headers"],
        json={"content": "Hacked comment"},
    )
    assert fail_edit.status_code == 403


@pytest.mark.asyncio
async def test_comment_deletion_permissions(async_client: AsyncClient):
    comm_owner = await create_user(async_client, "commdelowner", "commdelowner@example.com")
    post_author = await create_user(async_client, "postdelauthor", "postdelauthor@example.com")
    commenter = await create_user(async_client, "commdelcommenter", "commdelcommenter@example.com")
    random_user = await create_user(async_client, "randomdeluser", "randomdeluser@example.com")

    # 1. Community Owner creates community
    comm_resp = await async_client.post(
        "/api/v1/communities",
        headers=comm_owner["headers"],
        json={"name": "Moderated Discussion Space"},
    )
    comm_id = comm_resp.json()["id"]

    # 2. Post Author joins and creates post
    await async_client.post(f"/api/v1/communities/{comm_id}/join", headers=post_author["headers"])
    post_resp = await async_client.post(
        "/api/v1/posts",
        headers=post_author["headers"],
        json={"post_type": "text", "content": "Community post", "community_id": comm_id},
    )
    post_id = post_resp.json()["id"]

    # 3. Commenter joins and creates comment
    await async_client.post(f"/api/v1/communities/{comm_id}/join", headers=commenter["headers"])
    c_resp = await async_client.post(
        f"/api/v1/posts/{post_id}/comments",
        headers=commenter["headers"],
        json={"content": "First comment"},
    )
    c_id = c_resp.json()["id"]

    # 4. Random user cannot delete comment -> 403
    fail_del = await async_client.delete(f"/api/v1/comments/{c_id}", headers=random_user["headers"])
    assert fail_del.status_code == 403

    # 5. Post Author can delete comment -> 200
    post_author_del = await async_client.delete(f"/api/v1/comments/{c_id}", headers=post_author["headers"])
    assert post_author_del.status_code == 200

    # 6. Create another comment and verify Community Owner can delete it
    c2_resp = await async_client.post(
        f"/api/v1/posts/{post_id}/comments",
        headers=commenter["headers"],
        json={"content": "Second comment"},
    )
    c2_id = c2_resp.json()["id"]

    comm_owner_del = await async_client.delete(f"/api/v1/comments/{c2_id}", headers=comm_owner["headers"])
    assert comm_owner_del.status_code == 200
