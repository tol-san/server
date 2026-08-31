import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.users.models import Profile, User


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


async def create_admin_user(async_client: AsyncClient, db_session: AsyncSession, username: str, email: str):
    admin_user = User(
        email=email,
        username=username,
        hashed_password=get_password_hash("AdminPass123!"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(admin_user)
    await db_session.flush()

    admin_profile = Profile(
        user_id=admin_user.id,
        display_name=f"Admin {username}",
    )
    db_session.add(admin_profile)
    await db_session.commit()

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "AdminPass123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    return {"id": admin_user.id, "username": username, "headers": headers}


@pytest.mark.asyncio
async def test_report_submission_and_admin_workflow(async_client: AsyncClient, db_session: AsyncSession):
    admin = await create_admin_user(async_client, db_session, "report_admin", "report_admin@example.com")
    reporter = await create_user(async_client, "report_user", "reporter@example.com")
    spammer = await create_user(async_client, "spammer_user", "spammer@example.com")

    # 1. Create spam post
    post_resp = await async_client.post(
        "/api/v1/posts",
        headers=spammer["headers"],
        json={"post_type": "text", "title": "Buy Cheap Crypto Now!", "content": "Visit scam.com"},
    )
    post_id = post_resp.json()["id"]

    # 2. Reporter files report against post
    report_payload = {
        "report_type": "post",
        "target_id": post_id,
        "reason": "spam",
        "description": "Blatant cryptocurrency scam advertisement.",
    }
    report_resp = await async_client.post("/api/v1/reports", headers=reporter["headers"], json=report_payload)
    assert report_resp.status_code == 201
    report_data = report_resp.json()
    report_id = report_data["id"]
    assert report_data["status"] == "PENDING"
    assert report_data["reason"] == "spam"

    # 3. Admin lists reports
    list_resp = await async_client.get("/api/v1/reports?status=PENDING", headers=admin["headers"])
    assert list_resp.status_code == 200
    assert any(r["id"] == report_id for r in list_resp.json()["items"])

    # 4. Admin moves report to REVIEWING
    review_resp = await async_client.patch(
        f"/api/v1/reports/{report_id}/status",
        headers=admin["headers"],
        json={"status": "REVIEWING", "resolution_notes": "Under review by trust & safety team."},
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "REVIEWING"

    # 5. Admin resolves report and suspends spammer user
    resolve_resp = await async_client.patch(
        f"/api/v1/reports/{report_id}/status",
        headers=admin["headers"],
        json={
            "status": "RESOLVED",
            "resolution_action": "user_suspended",
            "resolution_notes": "Scammer account deactivated.",
        },
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "RESOLVED"
    assert resolve_resp.json()["resolution_action"] == "user_suspended"
    revoked = await async_client.get("/api/v1/profiles/me", headers=spammer["headers"])
    assert revoked.status_code == 401

    duplicate = await async_client.post(
        "/api/v1/reports", headers=reporter["headers"], json=report_payload
    )
    assert duplicate.status_code == 201  # terminal reports may be filed again


@pytest.mark.asyncio
async def test_community_owner_moderation_permissions(async_client: AsyncClient):
    comm_owner = await create_user(async_client, "mod_comm_owner", "mod_owner@example.com")
    member = await create_user(async_client, "mod_comm_member", "mod_member@example.com")
    outsider = await create_user(async_client, "mod_outsider", "mod_outsider@example.com")

    # Create community
    comm_resp = await async_client.post(
        "/api/v1/communities",
        headers=comm_owner["headers"],
        json={"name": "Moderated Tech Space"},
    )
    comm_id = comm_resp.json()["id"]

    # Member joins and posts
    await async_client.post(f"/api/v1/communities/{comm_id}/join", headers=member["headers"])
    post_resp = await async_client.post(
        "/api/v1/posts",
        headers=member["headers"],
        json={"post_type": "text", "title": "Flaming Argument", "community_id": comm_id},
    )
    post_id = post_resp.json()["id"]

    # Outsider reports the post in this community
    report_resp = await async_client.post(
        "/api/v1/reports",
        headers=outsider["headers"],
        json={
            "report_type": "post",
            "target_id": post_id,
            "community_id": comm_id,
            "reason": "harassment",
        },
    )
    assert report_resp.status_code == 201
    report_id = report_resp.json()["id"]

    # 1. Community owner can list reports for their own community
    owner_list = await async_client.get(f"/api/v1/reports?community_id={comm_id}", headers=comm_owner["headers"])
    assert owner_list.status_code == 200
    assert any(r["id"] == report_id for r in owner_list.json()["items"])

    # 2. Community owner can resolve the report
    owner_resolve = await async_client.patch(
        f"/api/v1/reports/{report_id}/status",
        headers=comm_owner["headers"],
        json={"status": "RESOLVED", "resolution_action": "dismissed", "resolution_notes": "Warning issued in chat."},
    )
    assert owner_resolve.status_code == 200
    assert owner_resolve.json()["status"] == "RESOLVED"

    # 3. Regular member attempting to list reports gets 403 Forbidden
    forbidden_resp = await async_client.get("/api/v1/reports", headers=member["headers"])
    assert forbidden_resp.status_code == 403


@pytest.mark.asyncio
async def test_report_scope_is_derived_from_target(async_client: AsyncClient):
    reporter = await create_user(async_client, "scope_reporter", "scope_reporter@example.com")
    author = await create_user(async_client, "scope_author", "scope_author@example.com")
    owner = await create_user(async_client, "scope_owner", "scope_owner@example.com")
    community = await async_client.post(
        "/api/v1/communities",
        headers=owner["headers"],
        json={"name": "Scope Community"},
    )
    community_id = community.json()["id"]
    post = await async_client.post(
        "/api/v1/posts",
        headers=author["headers"],
        json={"post_type": "text", "content": "personal target"},
    )
    response = await async_client.post(
        "/api/v1/reports",
        headers=reporter["headers"],
        json={
            "report_type": "post",
            "target_id": post.json()["id"],
            "community_id": community_id,
            "reason": "spam",
        },
    )
    assert response.status_code == 400
