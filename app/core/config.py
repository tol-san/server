from typing import List, Union
from pydantic import AnyHttpUrl, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Project Info
    PROJECT_NAME: str = "GenZ Media API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5433
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "genz_media"
    DATABASE_URL: Union[str, None] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ASYNC_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # JWT Authentication
    SECRET_KEY: str = "development-secret-key-change-in-production-min-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 7
    SIGNUP_OTP_EXPIRE_MINUTES: int = 7

    # Redis / Cache / PubSub
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO / S3 Object Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "genz-media"
    MINIO_SECURE: bool = False
    MINIO_PUBLIC_URL: str = "http://localhost:9000"

    # Meilisearch
    MEILISEARCH_URL: str = "http://localhost:7700"
    MEILISEARCH_MASTER_KEY: str = "meilisearch_master_key_12345"

    # LiveKit (WebRTC streaming provider)
    LIVEKIT_URL: str = "ws://localhost:7880"
    LIVEKIT_API_KEY: str = "devkey"
    LIVEKIT_API_SECRET: str = "secret"

    # WebSocket Ticket Authentication
    WS_TICKET_TTL_SECONDS: int = 60

    # Community Chat Rate Limiting
    CHAT_RATE_LIMIT_MESSAGES: int = 10   # messages allowed per window
    CHAT_RATE_LIMIT_WINDOW_SECONDS: int = 10

    # Background Workers (Outbox Relay + Stream Consumers)
    OUTBOX_POLL_INTERVAL_SECONDS: float = 1.0
    OUTBOX_BATCH_SIZE: int = 50
    WORKER_MAX_RETRIES: int = 3
    DEAD_LETTER_AFTER_RETRIES: int = 3
    WORKER_BLOCK_MS: int = 2000  # Redis Streams BLOCK timeout

    # SMTP / Email Configuration
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_STARTTLS: bool = False
    SMTP_USE_SSL: bool = False
    EMAILS_FROM_EMAIL: str = "noreply@genzmedia.app"
    EMAILS_FROM_NAME: str = "GenZ Media"
    FRONTEND_URL: str = "http://localhost:3000"

    # Observability
    ENABLE_METRICS: bool = True
    LOG_FORMAT: str = "json"  # "json" or "text" (text for local dev)


settings = Settings()
