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
async def test_event_driven_notifications(async_client: AsyncClient):
    alice = await create_user(async_client, "notif_alice", "notif_alice@example.com")
    bob = await create_user(async_client, "notif_bob", "notif_bob@example.com")

    # 1. Trigger: Bob follows Alice -> new_follower notification for Alice
    follow_resp = await async_client.post(f"/api/v1/users/{alice['id']}/follow", headers=bob["headers"])
    assert follow_resp.status_code == 200

    alice_notifs = await async_client.get("/api/v1/notifications", headers=alice["headers"])
    assert alice_notifs.status_code == 200
    items = alice_notifs.json()["items"]
    assert len(items) >= 1
    assert items[0]["notification_type"] == "new_follower"
    assert items[0]["actor"]["username"] == "notif_bob"

    # 2. Trigger: Alice creates post, Bob likes post -> post_like notification for Alice
    post_resp = await async_client.post(
        "/api/v1/posts",
        headers=alice["headers"],
        json={"post_type": "text", "title": "My Exciting Announcement", "content": "Hello World!"},
    )
    post_id = post_resp.json()["id"]

    like_resp = await async_client.post(f"/api/v1/posts/{post_id}/like", headers=bob["headers"])
    assert like_resp.status_code == 200

    alice_notifs = await async_client.get("/api/v1/notifications", headers=alice["headers"])
    assert alice_notifs.status_code == 200
    types = [n["notification_type"] for n in alice_notifs.json()["items"]]
    assert "post_like" in types

    # 3. Trigger: Bob comments on Alice's post -> post_comment notification for Alice
    comm_resp = await async_client.post(
        f"/api/v1/posts/{post_id}/comments",
        headers=bob["headers"],
        json={"content": "Awesome announcement!"},
    )
    comment_id = comm_resp.json()["id"]

    alice_notifs = await async_client.get("/api/v1/notifications", headers=alice["headers"])
    types = [n["notification_type"] for n in alice_notifs.json()["items"]]
    assert "post_comment" in types

    # 4. Trigger: Alice replies to Bob's comment -> comment_reply notification for Bob
    reply_resp = await async_client.post(
        f"/api/v1/posts/{post_id}/comments",
        headers=alice["headers"],
        json={"content": "Thanks Bob!", "parent_id": comment_id},
    )
    assert reply_resp.status_code == 201

    bob_notifs = await async_client.get("/api/v1/notifications", headers=bob["headers"])
    assert bob_notifs.status_code == 200
    bob_types = [n["notification_type"] for n in bob_notifs.json()["items"]]
    assert "comment_reply" in bob_types


@pytest.mark.asyncio
async def test_community_join_approval_notification(async_client: AsyncClient):
    owner = await create_user(async_client, "notif_owner", "owner@example.com")
    member = await create_user(async_client, "notif_member", "member@example.com")

    # Create private community
    comm_resp = await async_client.post(
        "/api/v1/communities",
        headers=owner["headers"],
        json={"name": "VIP Secret Society", "is_private": True},
    )
    comm_id = comm_resp.json()["id"]

    # Member requests to join
    join_req_resp = await async_client.post(f"/api/v1/communities/{comm_id}/join", headers=member["headers"])
    assert join_req_resp.status_code == 200

    # Get join requests
    requests_resp = await async_client.get(f"/api/v1/communities/{comm_id}/join-requests", headers=owner["headers"])
    request_id = requests_resp.json()["items"][0]["id"]

    # Owner approves request
    appr_resp = await async_client.post(
        f"/api/v1/communities/{comm_id}/join-requests/{request_id}/approve",
        headers=owner["headers"],
    )
    assert appr_resp.status_code == 200

    # Verify member receives community_join_approved notification
    member_notifs = await async_client.get("/api/v1/notifications", headers=member["headers"])
    assert member_notifs.status_code == 200
    types = [n["notification_type"] for n in member_notifs.json()["items"]]
    assert "community_join_approved" in types


@pytest.mark.asyncio
async def test_notification_management_workflow(async_client: AsyncClient):
    user = await create_user(async_client, "notif_manager", "notif_manager@example.com")
    other = await create_user(async_client, "notif_actor", "notif_actor@example.com")

    # Trigger follow to generate notification
    await async_client.post(f"/api/v1/users/{user['id']}/follow", headers=other["headers"])

    # 1. Unread count query
    unread_resp = await async_client.get("/api/v1/notifications/unread-count", headers=user["headers"])
    assert unread_resp.status_code == 200
    assert unread_resp.json()["unread_count"] >= 1

    # 2. List with unread_only filter
    list_resp = await async_client.get("/api/v1/notifications?unread_only=true", headers=user["headers"])
    assert list_resp.status_code == 200
    notif_id = list_resp.json()["items"][0]["id"]
    assert list_resp.json()["items"][0]["is_read"] is False

    # 3. Mark single notification as read
    read_resp = await async_client.patch(f"/api/v1/notifications/{notif_id}/read", headers=user["headers"])
    assert read_resp.status_code == 200
    assert read_resp.json()["is_read"] is True

    # 4. Mark all as read
    read_all_resp = await async_client.post("/api/v1/notifications/read-all", headers=user["headers"])
    assert read_all_resp.status_code == 200

    # Verify unread count is 0
    unread_resp2 = await async_client.get("/api/v1/notifications/unread-count", headers=user["headers"])
    assert unread_resp2.json()["unread_count"] == 0

    # 5. Delete notification
    del_resp = await async_client.delete(f"/api/v1/notifications/{notif_id}", headers=user["headers"])
    assert del_resp.status_code == 200


@pytest.mark.asyncio
async def test_typing_indicator_pubsub(async_client: AsyncClient):
    user = await create_user(async_client, "typing_user", "typing@example.com")
    community = await async_client.post(
        "/api/v1/communities",
        headers=user["headers"],
        json={"name": "Typing Community"},
    )

    payload = {"channel": community.json()["id"], "is_typing": True}
    resp = await async_client.post("/api/v1/notifications/typing", headers=user["headers"], json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
