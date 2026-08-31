import asyncio
import io
import json
import logging
from datetime import timedelta
from typing import BinaryIO, Optional, Union
from urllib.parse import urlparse
import uuid
from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings
from app.core.exceptions import BadRequestException, ServiceUnavailableException

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

    def ensure_bucket_exists(
        self, bucket_name: Optional[str] = None, *, public_assets: bool = True
    ) -> None:
        """Create a bucket and enforce its intended read policy."""
        bucket = bucket_name or settings.MINIO_BUCKET_NAME
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info("Created MinIO bucket: %s", bucket)

            if public_assets:
                # Only profile/community presentation assets are anonymous. Post
                # media is always served with a short-lived signed URL.
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject"],
                            "Resource": [
                                f"arn:aws:s3:::{bucket}/avatars/*",
                                f"arn:aws:s3:::{bucket}/communities/*",
                            ],
                        }
                    ],
                }
                self.client.set_bucket_policy(bucket, json.dumps(policy))
            else:
                try:
                    self.client.delete_bucket_policy(bucket)
                except S3Error as exc:
                    if exc.code not in {"NoSuchBucketPolicy", "NoSuchBucket"}:
                        raise
        except Exception as exc:
            logger.error("MinIO bucket initialization failed: %s", exc)
            raise ServiceUnavailableException("Media storage is temporarily unavailable.") from exc

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
            logger.info("Rejected image during safe decoding: %s", exc)
            raise BadRequestException("The uploaded image could not be processed safely.")

    def _upload_file_sync(
        self,
        file_data: Union[bytes, BinaryIO],
        object_name: str,
        content_type: str,
        bucket_name: Optional[str] = None,
        public_assets: bool = True,
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
            self.ensure_bucket_exists(bucket, public_assets=public_assets)
            self.client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=data_stream,
                length=length,
                content_type=content_type,
            )
            if public_assets:
                return f"{settings.MINIO_PUBLIC_URL.rstrip('/')}/{bucket}/{object_name}"
            return f"s3://{bucket}/{object_name}"
        except Exception as exc:
            if isinstance(exc, ServiceUnavailableException):
                raise
            logger.error("MinIO upload failed: %s", exc)
            raise ServiceUnavailableException("Media upload failed.") from exc

    async def upload_file(
        self,
        file_data: Union[bytes, BinaryIO],
        object_name: str,
        content_type: str,
        bucket_name: Optional[str] = None,
        public_assets: bool = True,
    ) -> str:
        return await asyncio.to_thread(
            self._upload_file_sync,
            file_data,
            object_name,
            content_type,
            bucket_name,
            public_assets,
        )

    def _parse_storage_url(self, url: str) -> tuple[str, str]:
        parsed = urlparse(url)
        if parsed.scheme == "s3":
            return parsed.netloc, parsed.path.lstrip("/")
        path = parsed.path.lstrip("/")
        bucket, separator, object_name = path.partition("/")
        if not separator or not bucket or not object_name:
            raise BadRequestException("Invalid media URL.")
        return bucket, object_name

    def normalize_owned_post_media_url(
        self, user_id: uuid.UUID, url: str, media_type: str
    ) -> str:
        bucket, object_name = self._parse_storage_url(url)
        if bucket not in {
            settings.MINIO_BUCKET_NAME,
            settings.MINIO_PRIVATE_BUCKET_NAME,
        }:
            raise BadRequestException("Post media must come from the media upload endpoint.")
        expected_prefix = f"posts/{user_id}/"
        expected_segment = "/images/" if media_type == "image" else "/videos/"
        if not object_name.startswith(expected_prefix) or expected_segment not in f"/{object_name}":
            raise BadRequestException("Post media does not belong to the current user.")
        return f"s3://{bucket}/{object_name}"

    def get_post_media_url(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        bucket, object_name = self._parse_storage_url(url)
        try:
            return self.client.presigned_get_object(
                bucket, object_name, expires=timedelta(minutes=15)
            )
        except Exception as exc:
            logger.error("Failed to sign media URL: %s", exc)
            raise ServiceUnavailableException("Media storage is temporarily unavailable.") from exc

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
        public_url = await self.upload_file(
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
            canonical_url = await self.upload_file(
                file_data=webp_bytes,
                object_name=object_name,
                content_type="image/webp",
                bucket_name=settings.MINIO_PRIVATE_BUCKET_NAME,
                public_assets=False,
            )
            return {
                "url": self.get_post_media_url(canonical_url),
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

            is_iso_media = (
                content_type in {"video/mp4", "video/quicktime"}
                and len(raw_bytes) >= 12
                and raw_bytes[4:8] == b"ftyp"
            )
            is_webm = (
                content_type == "video/webm"
                and raw_bytes.startswith(b"\x1a\x45\xdf\xa3")
            )
            if not (is_iso_media or is_webm):
                raise BadRequestException(
                    "The uploaded file contents do not match the declared video format."
                )

            ext = ALLOWED_POST_VIDEO_TYPES[content_type]
            object_name = f"posts/{user_id}/videos/{uuid.uuid4()}{ext}"
            canonical_url = await self.upload_file(
                file_data=raw_bytes,
                object_name=object_name,
                content_type=content_type,
                bucket_name=settings.MINIO_PRIVATE_BUCKET_NAME,
                public_assets=False,
            )
            return {
                "url": self.get_post_media_url(canonical_url),
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
            bucket_name, object_name = self._parse_storage_url(url)
            if bucket_name in {
                settings.MINIO_BUCKET_NAME,
                settings.MINIO_PRIVATE_BUCKET_NAME,
            }:
                await self.delete_file(object_name, bucket_name)
        except Exception as exc:
            logger.warning("Error parsing URL '%s' for deletion: %s", url, exc)


storage_service = StorageService()
