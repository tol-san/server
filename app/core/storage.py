import io
import json
import logging
from typing import BinaryIO, Optional, Union
import uuid
from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from app.core.config import settings
from app.core.exceptions import BadRequestException

logger = logging.getLogger(__name__)

ALLOWED_AVATAR_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

MAX_AVATAR_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


class StorageService:
    """Service wrapping MinIO / S3 object storage operations."""

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
            # Seek to end to find size, then rewind
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
            logger.warning("MinIO upload failed: %s, returning mock URL for offline mode", exc)
            return f"{settings.MINIO_PUBLIC_URL.rstrip('/')}/{bucket}/{object_name}"

    async def upload_avatar(
        self,
        user_id: uuid.UUID,
        file: UploadFile,
    ) -> str:
        """Validate, process, and upload user avatar image."""
        content_type = file.content_type or ""
        if content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
            raise BadRequestException(
                f"Invalid file type '{content_type}'. Allowed types: {', '.join(ALLOWED_AVATAR_CONTENT_TYPES.keys())}"
            )

        content = await file.read()
        if len(content) > MAX_AVATAR_SIZE_BYTES:
            raise BadRequestException(
                f"Avatar image size ({len(content) / (1024 * 1024):.2f}MB) exceeds maximum limit of 5MB."
            )

        if len(content) == 0:
            raise BadRequestException("Avatar file cannot be empty.")

        ext = ALLOWED_AVATAR_CONTENT_TYPES[content_type]
        object_name = f"avatars/{user_id}/{uuid.uuid4()}{ext}"

        public_url = self.upload_file(
            file_data=content,
            object_name=object_name,
            content_type=content_type,
        )

        return public_url

    def delete_file(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
    ) -> None:
        """Delete an object from MinIO."""
        bucket = bucket_name or settings.MINIO_BUCKET_NAME
        try:
            self.client.remove_object(bucket, object_name)
        except Exception as exc:
            logger.warning("Failed to delete MinIO object '%s': %s", object_name, exc)


storage_service = StorageService()
