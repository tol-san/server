import pytest
from httpx import AsyncClient


async def create_user_and_login(async_client: AsyncClient, username: str, email: str, user_agent: str = "TestBrowser"):
    payload = {
        "email": email,
        "username": username,
        "password": "Password123!",
        "display_name": f"User {username}",
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=payload)
    assert reg_resp.status_code == 201

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "Password123!"},
        headers={"User-Agent": user_agent},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    return {
        "email": email,
        "access_token": token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
        "headers": headers,
    }


@pytest.mark.asyncio
async def test_session_creation_and_listing(async_client: AsyncClient):
    session1 = await create_user_and_login(
        async_client,
        "session_user",
        "session_user@example.com",
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
    )

    # List active sessions
    resp = await async_client.get("/api/v1/auth/sessions", headers=session1["headers"])
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) >= 1
    assert sessions[0]["device_name"] == "iPhone"
    assert sessions[0]["is_current"] is True


@pytest.mark.asyncio
async def test_multiple_sessions_and_revoke_other(async_client: AsyncClient):
    # Log in first time (Session A: iPhone)
    session_a = await create_user_and_login(
        async_client,
        "multi_session_user",
        "multi_session@example.com",
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)",
    )

    # Log in second time (Session B: Android)
    login_b = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "multi_session@example.com", "password": "Password123!"},
        headers={"User-Agent": "Mozilla/5.0 (Linux; Android 14)"},
    )
    assert login_b.status_code == 200
    session_b_token = login_b.json()["access_token"]
    session_b_headers = {"Authorization": f"Bearer {session_b_token}"}

    # Verify both sessions are visible
    list_resp = await async_client.get("/api/v1/auth/sessions", headers=session_b_headers)
    assert list_resp.status_code == 200
    active_sessions = list_resp.json()
    assert len(active_sessions) == 2

    # Revoke other sessions from Session B
    revoke_resp = await async_client.delete("/api/v1/auth/sessions/other", headers=session_b_headers)
    assert revoke_resp.status_code == 200
    assert "Successfully signed out" in revoke_resp.json()["message"]

    # Now only 1 session should remain
    list_resp2 = await async_client.get("/api/v1/auth/sessions", headers=session_b_headers)
    assert list_resp2.status_code == 200
    assert len(list_resp2.json()) == 1
    assert list_resp2.json()[0]["device_name"] == "Android Device"


@pytest.mark.asyncio
async def test_revoke_individual_session(async_client: AsyncClient):
    session = await create_user_and_login(
        async_client,
        "revoke_user",
        "revoke_user@example.com",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    )

    list_resp = await async_client.get("/api/v1/auth/sessions", headers=session["headers"])
    session_id = list_resp.json()[0]["id"]

    # Revoke that session
    del_resp = await async_client.delete(f"/api/v1/auth/sessions/{session_id}", headers=session["headers"])
    assert del_resp.status_code == 200
    assert del_resp.json()["message"] == "Session successfully revoked."

    # Now session list should be empty
    list_resp2 = await async_client.get("/api/v1/auth/sessions", headers=session["headers"])
    assert len(list_resp2.json()) == 0
