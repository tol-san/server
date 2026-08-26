from app.core.config import Settings, settings


def test_settings_initialization():
    assert settings.PROJECT_NAME == "GenZ Media API"
    assert settings.VERSION == "0.1.0"
    assert settings.API_V1_STR == "/api/v1"
    assert isinstance(settings.BACKEND_CORS_ORIGINS, list)
    assert settings.ALGORITHM == "HS256"


def test_async_database_uri():
    custom_settings = Settings(
        POSTGRES_USER="test_user",
        POSTGRES_PASSWORD="test_password",
        POSTGRES_SERVER="db.example.com",
        POSTGRES_PORT=5433,
        POSTGRES_DB="test_db",
    )
    expected_uri = "postgresql+asyncpg://test_user:test_password@db.example.com:5433/test_db"
    assert custom_settings.ASYNC_DATABASE_URI == expected_uri


def test_async_database_uri_override():
    custom_settings = Settings(
        DATABASE_URL="postgresql+asyncpg://custom_url:5432/custom_db"
    )
    assert custom_settings.ASYNC_DATABASE_URI == "postgresql+asyncpg://custom_url:5432/custom_db"
