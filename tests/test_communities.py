import io
import pytest
from httpx import AsyncClient
from PIL import Image


def create_test_image_bytes(format_name: str = "PNG", size: tuple[int, int] = (600, 300)) -> bytes:
    img = Image.new("RGB", size, color=(100, 150, 200))
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
async def test_create_public_and_private_communities(async_client: AsyncClient):
    owner = await create_user(async_client, "commowner1", "commowner1@example.com")

    # 1. Public community
    pub_payload = {
        "name": "Flutter Developers",
        "description": "Cross-platform mobile development space",
        "is_private": False,
    }
    pub_resp = await async_client.post(
        "/api/v1/communities",
        headers=owner["headers"],
        json=pub_payload,
    )
    assert pub_resp.status_code == 201
    pub_data = pub_resp.json()
    assert pub_data["name"] == "Flutter Developers"
    assert pub_data["slug"] == "flutter-developers"
    assert pub_data["is_private"] is False
    assert pub_data["member_count"] == 1
    assert pub_data["owner_id"] == owner["id"]

    # 2. Private community
    priv_payload = {
        "name": "Secret Beta Testers",
        "description": "Exclusive invitation-only testers group",
        "is_private": True,
    }
    priv_resp = await async_client.post(
        "/api/v1/communities",
        headers=owner["headers"],
        json=priv_payload,
    )
    assert priv_resp.status_code == 201
    priv_data = priv_resp.json()
    assert priv_data["is_private"] is True


@pytest.mark.asyncio
async def test_community_details_and_updates(async_client: AsyncClient):
    owner = await create_user(async_client, "owner2", "owner2@example.com")
    other_user = await create_user(async_client, "other2", "other2@example.com")

    # Create community
    comm_resp = await async_client.post(
        "/api/v1/communities",
        headers=owner["headers"],
        json={"name": "UI UX Designers", "description": "Designers club"},
    )
    comm_id = comm_resp.json()["id"]

    # Owner updates community
    update_resp = await async_client.patch(
        f"/api/v1/communities/{comm_id}",
        headers=owner["headers"],
        json={"description": "Updated designers club description"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["description"] == "Updated designers club description"

    # Non-owner fails to update
    fail_update = await async_client.patch(
        f"/api/v1/communities/{comm_id}",
        headers=other_user["headers"],
        json={"description": "Hacked description"},
    )
    assert fail_update.status_code == 403

    # View details
    detail_resp = await async_client.get(f"/api/v1/communities/{comm_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["name"] == "UI UX Designers"


@pytest.mark.asyncio
async def test_public_community_join_and_leave(async_client: AsyncClient):
    owner = await create_user(async_client, "pubowner", "pubowner@example.com")
    member = await create_user(async_client, "pubmember", "pubmember@example.com")

    comm_resp = await async_client.post(
        "/api/v1/communities",
        headers=owner["headers"],
        json={"name": "Open Gaming Hub", "is_private": False},
    )
    comm_id = comm_resp.json()["id"]

    # 1. Member joins public community
    join_resp = await async_client.post(
        f"/api/v1/communities/{comm_id}/join",
        headers=member["headers"],
    )
    assert join_resp.status_code == 200
    assert join_resp.json()["status"] == "joined"
    assert join_resp.json()["is_member"] is True

    # 2. Check updated member count
    detail = await async_client.get(f"/api/v1/communities/{comm_id}")
    assert detail.json()["member_count"] == 2

    # 3. Duplicate join returns 400
    dup_join = await async_client.post(
        f"/api/v1/communities/{comm_id}/join",
        headers=member["headers"],
    )
    assert dup_join.status_code == 400

    # 4. Member leaves community
    leave_resp = await async_client.delete(
        f"/api/v1/communities/{comm_id}/leave",
        headers=member["headers"],
    )
    assert leave_resp.status_code == 200

    # 5. Member count returns to 1
    detail_after = await async_client.get(f"/api/v1/communities/{comm_id}")
    assert detail_after.json()["member_count"] == 1

    # 6. Owner cannot leave
    owner_leave = await async_client.delete(
        f"/api/v1/communities/{comm_id}/leave",
        headers=owner["headers"],
    )
    assert owner_leave.status_code == 400


@pytest.mark.asyncio
async def test_private_community_join_requests_flow(async_client: AsyncClient):
    owner = await create_user(async_client, "privowner", "privowner@example.com")
    applicant = await create_user(async_client, "applicant", "applicant@example.com")

    comm_resp = await async_client.post(
        "/api/v1/communities",
        headers=owner["headers"],
        json={"name": "Exclusive Club", "is_private": True},
    )
    comm_id = comm_resp.json()["id"]

    # 1. Applicant submits join request
    join_resp = await async_client.post(
        f"/api/v1/communities/{comm_id}/join",
        headers=applicant["headers"],
    )
    assert join_resp.status_code == 200
    assert join_resp.json()["status"] == "pending"
    assert join_resp.json()["is_member"] is False

    hidden_detail = await async_client.get(f"/api/v1/communities/{comm_id}")
    assert hidden_detail.status_code == 404
    hidden_members = await async_client.get(f"/api/v1/communities/{comm_id}/members")
    assert hidden_members.status_code == 404

    # 2. Owner lists join requests
    requests_resp = await async_client.get(
        f"/api/v1/communities/{comm_id}/join-requests",
        headers=owner["headers"],
    )
    assert requests_resp.status_code == 200
    req_data = requests_resp.json()
    assert req_data["total"] == 1
    assert req_data["items"][0]["username"] == "applicant"
    request_id = req_data["items"][0]["id"]

    # 3. Non-owner cannot list requests
    fail_list = await async_client.get(
        f"/api/v1/communities/{comm_id}/join-requests",
        headers=applicant["headers"],
    )
    assert fail_list.status_code == 403

    # 4. Owner approves join request
    approve_resp = await async_client.post(
        f"/api/v1/communities/{comm_id}/join-requests/{request_id}/approve",
        headers=owner["headers"],
    )
    assert approve_resp.status_code == 200

    # 5. Verify member count and member list
    detail = await async_client.get(
        f"/api/v1/communities/{comm_id}", headers=applicant["headers"]
    )
    assert detail.json()["member_count"] == 2

    members_resp = await async_client.get(
        f"/api/v1/communities/{comm_id}/members", headers=applicant["headers"]
    )
    assert members_resp.status_code == 200
    usernames = [m["username"] for m in members_resp.json()["items"]]
    assert "applicant" in usernames


@pytest.mark.asyncio
async def test_kick_member_and_delete_community(async_client: AsyncClient):
    owner = await create_user(async_client, "modowner", "modowner@example.com")
    member = await create_user(async_client, "troublemaker", "troublemaker@example.com")

    # Create & join
    comm_resp = await async_client.post(
        "/api/v1/communities",
        headers=owner["headers"],
        json={"name": "Moderation Test Community", "is_private": False},
    )
    comm_id = comm_resp.json()["id"]
    await async_client.post(f"/api/v1/communities/{comm_id}/join", headers=member["headers"])

    # Owner kicks member
    kick_resp = await async_client.delete(
        f"/api/v1/communities/{comm_id}/members/{member['id']}",
        headers=owner["headers"],
    )
    assert kick_resp.status_code == 200

    # Verify member count = 1
    detail = await async_client.get(f"/api/v1/communities/{comm_id}")
    assert detail.json()["member_count"] == 1

    # Delete community
    del_resp = await async_client.delete(f"/api/v1/communities/{comm_id}", headers=owner["headers"])
    assert del_resp.status_code == 200

    # Confirm 404
    get_after = await async_client.get(f"/api/v1/communities/{comm_id}")
    assert get_after.status_code == 404


@pytest.mark.asyncio
async def test_upload_community_cover(async_client: AsyncClient):
    owner = await create_user(async_client, "coverowner", "coverowner@example.com")
    comm_resp = await async_client.post(
        "/api/v1/communities",
        headers=owner["headers"],
        json={"name": "Cover Art Community"},
    )
    comm_id = comm_resp.json()["id"]

    cover_bytes = create_test_image_bytes("PNG", (800, 400))
    files = {"file": ("banner.png", io.BytesIO(cover_bytes), "image/png")}

    upload_resp = await async_client.post(
        f"/api/v1/communities/{comm_id}/cover",
        headers=owner["headers"],
        files=files,
    )
    assert upload_resp.status_code == 200
    data = upload_resp.json()
    assert data["cover_image_url"] is not None
    assert "communities/" in data["cover_image_url"]
    assert data["cover_image_url"].endswith(".webp")
