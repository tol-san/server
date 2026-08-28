import asyncio
import io
import json
import logging
from typing import BinaryIO, Optional, Union
from urllib.parse import urlparse
import uuid
from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings
from app.core.exceptions import BadRequestException

logger = logging.getLogger(__name__)

ALLOWED_AVATAR_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}

ALLOWED_POST_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}

ALLOWED_POST_VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}

MAX_AVATAR_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_POST_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_POST_VIDEO_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
DEFAULT_AVATAR_MAX_DIMENSION = 512  # Standard mobile profile resolution
DEFAULT_POST_IMAGE_MAX_DIMENSION = 1920  # High-definition post resolution
DEFAULT_WEBP_QUALITY = 85


class StorageService:
    """Service wrapping MinIO / S3 object storage operations with image processing."""

    def __init__(self) -> None:
        self._client: Optional[Minio] = None

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
        return self._client

    def ensure_bucket_exists(self, bucket_name: Optional[str] = None) -> None:
        """Create bucket if it doesn't exist and set public read policy for media."""
        bucket = bucket_name or settings.MINIO_BUCKET_NAME
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info("Created MinIO bucket: %s", bucket)

                # Set public read access policy on bucket
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{bucket}/*"],
                        }
                    ],
                }
                self.client.set_bucket_policy(bucket, json.dumps(policy))
                logger.info("Applied public read policy to bucket: %s", bucket)
        except Exception as exc:
            logger.warning("MinIO bucket initialization failed or offline: %s", exc)

    def process_and_convert_to_webp(
        self,
        image_bytes: bytes,
        max_dimension: int = DEFAULT_AVATAR_MAX_DIMENSION,
        quality: int = DEFAULT_WEBP_QUALITY,
    ) -> bytes:
        """Validate, sanitize, auto-orient, resize and convert image to WebP."""
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Correct orientation from EXIF and strip all metadata
                img = ImageOps.exif_transpose(img)

                # Handle color modes
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    img = img.convert("RGBA")
                else:
                    img = img.convert("RGB")

                # Resize if larger than max_dimension
                if img.width > max_dimension or img.height > max_dimension:
                    img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

                # Save as optimized WebP
                output_buffer = io.BytesIO()
                img.save(output_buffer, format="WEBP", quality=quality, method=6)
                return output_buffer.getvalue()
        except UnidentifiedImageError:
            raise BadRequestException("The uploaded file is not a valid or readable image.")
        except Exception as exc:
            raise BadRequestException(f"Failed to process image file: {str(exc)}")

    def upload_file(
        self,
        file_data: Union[bytes, BinaryIO],
        object_name: str,
        content_type: str,
        bucket_name: Optional[str] = None,
    ) -> str:
        """Upload a file or byte stream to MinIO and return its public URL."""
        bucket = bucket_name or settings.MINIO_BUCKET_NAME

        if isinstance(file_data, bytes):
            data_stream = io.BytesIO(file_data)
            length = len(file_data)
        else:
            data_stream = file_data
            file_data.seek(0, io.SEEK_END)
            length = file_data.tell()
            file_data.seek(0)

        try:
            self.ensure_bucket_exists(bucket)
            self.client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=data_stream,
                length=length,
                content_type=content_type,
            )
            return f"{settings.MINIO_PUBLIC_URL.rstrip('/')}/{bucket}/{object_name}"
        except Exception as exc:
            logger.warning("MinIO upload failed: %s, returning fallback URL", exc)
            return f"{settings.MINIO_PUBLIC_URL.rstrip('/')}/{bucket}/{object_name}"

    async def upload_avatar(
        self,
        user_id: uuid.UUID,
        file: UploadFile,
        old_avatar_url: Optional[str] = None,
    ) -> str:
        """Validate, convert to WebP, clean up previous avatar, and upload new avatar."""
        content_type = (file.content_type or "").lower()
        if content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
            raise BadRequestException(
                f"Invalid file type '{content_type}'. Allowed types: {', '.join(ALLOWED_AVATAR_CONTENT_TYPES)}"
            )

        raw_bytes = await file.read()
        if len(raw_bytes) > MAX_AVATAR_SIZE_BYTES:
            raise BadRequestException(
                f"Avatar image size ({len(raw_bytes) / (1024 * 1024):.2f}MB) exceeds maximum limit of 5MB."
            )

        if len(raw_bytes) == 0:
            raise BadRequestException("Avatar file cannot be empty.")

        # Process and convert to optimized WebP
        webp_bytes = self.process_and_convert_to_webp(raw_bytes)

        # Delete old avatar from MinIO if it exists
        if old_avatar_url:
            await self.delete_file_by_url(old_avatar_url)

        # Upload new WebP avatar
        object_name = f"avatars/{user_id}/{uuid.uuid4()}.webp"
        public_url = self.upload_file(
            file_data=webp_bytes,
            object_name=object_name,
            content_type="image/webp",
        )

        return public_url

    async def upload_post_media(
        self,
        user_id: uuid.UUID,
        file: UploadFile,
    ) -> dict:
        """Upload post image (WebP) or short video (MP4/MOV/WebM) to MinIO."""
        content_type = (file.content_type or "").lower()

        # 1. Image upload
        if content_type in ALLOWED_POST_IMAGE_TYPES:
            raw_bytes = await file.read()
            if len(raw_bytes) > MAX_POST_IMAGE_SIZE_BYTES:
                raise BadRequestException("Post image size exceeds limit of 10MB.")
            if len(raw_bytes) == 0:
                raise BadRequestException("Image file cannot be empty.")

            webp_bytes = self.process_and_convert_to_webp(raw_bytes, max_dimension=DEFAULT_POST_IMAGE_MAX_DIMENSION)

            # Get dimensions from processed WebP
            with Image.open(io.BytesIO(webp_bytes)) as img:
                width, height = img.width, img.height

            object_name = f"posts/{user_id}/images/{uuid.uuid4()}.webp"
            public_url = self.upload_file(
                file_data=webp_bytes,
                object_name=object_name,
                content_type="image/webp",
            )
            return {
                "url": public_url,
                "media_type": "image",
                "thumbnail_url": None,
                "width": width,
                "height": height,
                "duration": None,
            }

        # 2. Video upload
        if content_type in ALLOWED_POST_VIDEO_TYPES:
            raw_bytes = await file.read()
            if len(raw_bytes) > MAX_POST_VIDEO_SIZE_BYTES:
                raise BadRequestException("Post video size exceeds limit of 50MB.")
            if len(raw_bytes) == 0:
                raise BadRequestException("Video file cannot be empty.")

            ext = ALLOWED_POST_VIDEO_TYPES[content_type]
            object_name = f"posts/{user_id}/videos/{uuid.uuid4()}{ext}"
            public_url = self.upload_file(
                file_data=raw_bytes,
                object_name=object_name,
                content_type=content_type,
            )
            return {
                "url": public_url,
                "media_type": "video",
                "thumbnail_url": None,
                "width": None,
                "height": None,
                "duration": None,
            }

        allowed_all = list(ALLOWED_POST_IMAGE_TYPES) + list(ALLOWED_POST_VIDEO_TYPES.keys())
        raise BadRequestException(f"Unsupported media format '{content_type}'. Allowed: {', '.join(allowed_all)}")

    async def delete_file(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
    ) -> None:
        """Delete an object from MinIO."""
        bucket = bucket_name or settings.MINIO_BUCKET_NAME
        try:
            await asyncio.to_thread(self.client.remove_object, bucket, object_name)
            logger.info("Deleted MinIO object: %s/%s", bucket, object_name)
        except Exception as exc:
            logger.warning("Failed to delete MinIO object '%s': %s", object_name, exc)

    async def delete_file_by_url(self, url: Optional[str]) -> None:
        """Parse object path from URL and delete from MinIO."""
        if not url:
            return
        try:
            parsed = urlparse(url)
            path = parsed.path.lstrip("/")
            bucket_name = settings.MINIO_BUCKET_NAME
            if path.startswith(bucket_name + "/"):
                object_name = path[len(bucket_name) + 1 :]
                await self.delete_file(object_name, bucket_name)
            elif "avatars/" in path or "posts/" in path or "communities/" in path:
                # Direct relative path
                await self.delete_file(path, bucket_name)
        except Exception as exc:
            logger.warning("Error parsing URL '%s' for deletion: %s", url, exc)


storage_service = StorageService()
