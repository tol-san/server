import io
import pytest
from httpx import AsyncClient
from PIL import Image

from app.core.config import settings
from app.core.storage import storage_service


def create_test_image_bytes(format_name: str = "PNG", size: tuple[int, int] = (600, 600)) -> bytes:
    """Helper to generate in-memory image bytes for testing."""
    img = Image.new("RGB", size, color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format=format_name)
    return buf.getvalue()


@pytest.fixture
async def authenticated_user(async_client: AsyncClient):
    reg_payload = {
        "email": "mobileavatar@example.com",
        "username": "mobileavataruser",
        "password": "Password123!",
        "display_name": "Mobile User",
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


@pytest.mark.asyncio
async def test_storage_service_upload_and_delete():
    storage_service.ensure_bucket_exists()
    test_content = b"fake image byte content"
    object_name = "test/sample_image.png"

    url = await storage_service.upload_file(
        file_data=test_content,
        object_name=object_name,
        content_type="image/png",
    )
    assert "sample_image.png" in url
    assert "genz-media" in url

    # Cleanup
    await storage_service.delete_file(object_name)


def test_process_and_convert_to_webp():
    # Create 800x800 test PNG
    raw_png = create_test_image_bytes("PNG", (800, 800))

    # Process to WebP with max 512px
    webp_bytes = storage_service.process_and_convert_to_webp(raw_png, max_dimension=512)
    assert len(webp_bytes) > 0

    # Verify output is valid WebP with dimension <= 512px
    with Image.open(io.BytesIO(webp_bytes)) as result_img:
        assert result_img.format == "WEBP"
        assert result_img.width <= 512
        assert result_img.height <= 512


def test_get_post_media_url_presigns_canonical_storage_url(mock_object_storage):
    canonical_url = "s3://genz-media-private/posts/user-id/videos/clip.mp4"

    resolved_url = storage_service.get_post_media_url(canonical_url)

    assert resolved_url == (
        "http://storage.test/genz-media-private/"
        "posts/user-id/videos/clip.mp4?signature=test"
    )
    mock_object_storage.presigned_get_object.assert_called_once()


def test_get_post_media_url_presigns_public_minio_url(mock_object_storage):
    minio_url = (
        f"{settings.MINIO_PUBLIC_URL.rstrip('/')}/genz-media-private/"
        "posts/user-id/images/photo.webp"
    )

    resolved_url = storage_service.get_post_media_url(minio_url)

    assert resolved_url == (
        "http://storage.test/genz-media-private/"
        "posts/user-id/images/photo.webp?signature=test"
    )
    mock_object_storage.presigned_get_object.assert_called_once()


def test_get_post_media_url_keeps_external_http_url(mock_object_storage):
    external_url = (
        "https://cdn.jsdelivr.net/gh/intel-iot-devkit/"
        "sample-videos@master/person-bicycle-car-detection.mp4"
    )

    resolved_url = storage_service.get_post_media_url(external_url)

    assert resolved_url == external_url
    mock_object_storage.presigned_get_object.assert_not_called()


@pytest.mark.asyncio
async def test_upload_avatar_converts_to_webp(async_client: AsyncClient, authenticated_user: dict):
    jpeg_bytes = create_test_image_bytes("JPEG", (300, 300))
    files = {
        "file": ("avatar.jpg", io.BytesIO(jpeg_bytes), "image/jpeg"),
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
    assert data["avatar_url"].endswith(".webp")  # Converted to WebP for mobile

    # Verify GET /profiles/me returns updated avatar_url
    get_resp = await async_client.get(
        "/api/v1/profiles/me",
        headers=authenticated_user["headers"],
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["avatar_url"] == data["avatar_url"]


@pytest.mark.asyncio
async def test_upload_avatar_replacement_and_cleanup(async_client: AsyncClient, authenticated_user: dict):
    # 1. Upload first avatar
    img1 = create_test_image_bytes("PNG", (200, 200))
    resp1 = await async_client.post(
        "/api/v1/profiles/me/avatar",
        headers=authenticated_user["headers"],
        files={"file": ("first.png", io.BytesIO(img1), "image/png")},
    )
    assert resp1.status_code == 200
    first_url = resp1.json()["avatar_url"]

    # 2. Upload second avatar (replaces first)
    img2 = create_test_image_bytes("JPEG", (250, 250))
    resp2 = await async_client.post(
        "/api/v1/profiles/me/avatar",
        headers=authenticated_user["headers"],
        files={"file": ("second.jpg", io.BytesIO(img2), "image/jpeg")},
    )
    assert resp2.status_code == 200
    second_url = resp2.json()["avatar_url"]
    assert second_url != first_url


@pytest.mark.asyncio
async def test_delete_avatar(async_client: AsyncClient, authenticated_user: dict):
    # 1. Upload avatar first
    img = create_test_image_bytes("PNG", (200, 200))
    await async_client.post(
        "/api/v1/profiles/me/avatar",
        headers=authenticated_user["headers"],
        files={"file": ("myavatar.png", io.BytesIO(img), "image/png")},
    )

    # 2. Delete avatar
    del_resp = await async_client.delete(
        "/api/v1/profiles/me/avatar",
        headers=authenticated_user["headers"],
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["avatar_url"] is None

    # 3. Verify GET /profiles/me shows avatar_url is None
    get_resp = await async_client.get(
        "/api/v1/profiles/me",
        headers=authenticated_user["headers"],
    )
    assert get_resp.json()["avatar_url"] is None


@pytest.mark.asyncio
async def test_upload_avatar_corrupted_file(async_client: AsyncClient, authenticated_user: dict):
    corrupted_bytes = b"Not a real image file at all"
    files = {
        "file": ("fake.jpg", io.BytesIO(corrupted_bytes), "image/jpeg"),
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
async def test_upload_avatar_invalid_mime(async_client: AsyncClient, authenticated_user: dict):
    files = {
        "file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf"),
    }

    response = await async_client.post(
        "/api/v1/profiles/me/avatar",
        headers=authenticated_user["headers"],
        files=files,
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_delete_avatar_unauthenticated(async_client: AsyncClient):
    response = await async_client.delete("/api/v1/profiles/me/avatar")
    assert response.status_code == 401
