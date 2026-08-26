import io
import pytest
from httpx import AsyncClient

from app.core.storage import storage_service


@pytest.fixture
async def authenticated_user(async_client: AsyncClient):
    reg_payload = {
        "email": "avataruser@example.com",
        "username": "avataruser",
        "password": "Password123!",
        "display_name": "Avatar User",
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": reg_payload["email"], "password": reg_payload["password"]},
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    return {"user": reg_payload, "token": access_token, "headers": headers}


def test_storage_service_upload_and_delete():
    storage_service.ensure_bucket_exists()
    test_content = b"fake image byte content"
    object_name = "test/sample_image.png"

    url = storage_service.upload_file(
        file_data=test_content,
        object_name=object_name,
        content_type="image/png",
    )
    assert "sample_image.png" in url
    assert "genz-media" in url

    # Cleanup
    storage_service.delete_file(object_name)


@pytest.mark.asyncio
async def test_upload_avatar_success(async_client: AsyncClient, authenticated_user: dict):
    fake_image_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"  # JPEG header bytes
    files = {
        "file": ("avatar.jpg", io.BytesIO(fake_image_bytes), "image/jpeg"),
    }

    response = await async_client.post(
        "/api/v1/profiles/me/avatar",
        headers=authenticated_user["headers"],
        files=files,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["avatar_url"] is not None
    assert "avatars/" in data["avatar_url"]
    assert data["avatar_url"].endswith(".jpg")

    # Verify GET /profiles/me returns updated avatar_url
    get_resp = await async_client.get(
        "/api/v1/profiles/me",
        headers=authenticated_user["headers"],
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["avatar_url"] == data["avatar_url"]


@pytest.mark.asyncio
async def test_upload_avatar_png(async_client: AsyncClient, authenticated_user: dict):
    fake_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    files = {
        "file": ("avatar.png", io.BytesIO(fake_png_bytes), "image/png"),
    }

    response = await async_client.post(
        "/api/v1/profiles/me/avatar",
        headers=authenticated_user["headers"],
        files=files,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["avatar_url"].endswith(".png")


@pytest.mark.asyncio
async def test_upload_avatar_invalid_content_type(async_client: AsyncClient, authenticated_user: dict):
    text_bytes = b"Hello, this is a plain text file, not an image."
    files = {
        "file": ("document.txt", io.BytesIO(text_bytes), "text/plain"),
    }

    response = await async_client.post(
        "/api/v1/profiles/me/avatar",
        headers=authenticated_user["headers"],
        files=files,
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_upload_avatar_empty_file(async_client: AsyncClient, authenticated_user: dict):
    empty_bytes = b""
    files = {
        "file": ("empty.jpg", io.BytesIO(empty_bytes), "image/jpeg"),
    }

    response = await async_client.post(
        "/api/v1/profiles/me/avatar",
        headers=authenticated_user["headers"],
        files=files,
    )
    assert response.status_code == 400
    data = response.json()
    assert "cannot be empty" in data["detail"].lower()


@pytest.mark.asyncio
async def test_upload_avatar_unauthenticated(async_client: AsyncClient):
    files = {
        "file": ("avatar.jpg", io.BytesIO(b"data"), "image/jpeg"),
    }
    response = await async_client.post("/api/v1/profiles/me/avatar", files=files)
    assert response.status_code == 401
