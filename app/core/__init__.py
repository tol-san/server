"""Core module containing configuration, security, database and shared utilities."""

from app.core.config import settings
from app.core.database import Base, TimestampMixin, get_db
from app.core.exceptions import (
    AppException,
    BadRequestException,
    EmailAlreadyExistsException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
    UsernameAlreadyExistsException,
    register_exception_handlers,
)
from app.core.meilisearch import (
    INDEX_COMMUNITIES,
    INDEX_CONFIGURATIONS,
    INDEX_INTERESTS,
    INDEX_POSTS,
    INDEX_USERS,
    MeilisearchService,
    close_meilisearch,
    get_meilisearch_client,
    init_meilisearch_indexes,
    meilisearch_service,
)
from app.core.redis import blacklist_token, get_redis_client, is_token_blacklisted
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.core.storage import StorageService, storage_service

__all__ = [
    "settings",
    "Base",
    "TimestampMixin",
    "get_db",
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "create_password_reset_token",
    "decode_token",
    "blacklist_token",
    "is_token_blacklisted",
    "get_redis_client",
    "StorageService",
    "storage_service",
    "MeilisearchService",
    "meilisearch_service",
    "get_meilisearch_client",
    "close_meilisearch",
    "init_meilisearch_indexes",
    "INDEX_USERS",
    "INDEX_COMMUNITIES",
    "INDEX_POSTS",
    "INDEX_INTERESTS",
    "INDEX_CONFIGURATIONS",
    "AppException",
    "BadRequestException",
    "EmailAlreadyExistsException",
    "UsernameAlreadyExistsException",
    "NotFoundException",
    "UnauthorizedException",
    "ForbiddenException",
    "register_exception_handlers",
]
