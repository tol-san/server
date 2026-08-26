import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.comments.router import router as comments_router
from app.communities.router import router as communities_router
from app.core import close_meilisearch, init_meilisearch_indexes
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.redis import close_redis
from app.interests.router import router as interests_router
from app.posts.router import router as posts_router
from app.profiles.router import router as profiles_router
from app.users.router import router as users_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await init_meilisearch_indexes()
    except Exception as exc:
        logger.warning("Meilisearch initial setup warning: %s", exc)

    yield

    # Shutdown
    await close_redis()
    await close_meilisearch()


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    # Set up CORS
    if settings.BACKEND_CORS_ORIGINS:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Register custom exception handlers
    register_exception_handlers(application)

    # Include routers
    application.include_router(auth_router, prefix=settings.API_V1_STR)
    application.include_router(users_router, prefix=settings.API_V1_STR)
    application.include_router(profiles_router, prefix=settings.API_V1_STR)
    application.include_router(interests_router, prefix=settings.API_V1_STR)
    application.include_router(communities_router, prefix=settings.API_V1_STR)
    application.include_router(posts_router, prefix=settings.API_V1_STR)
    application.include_router(comments_router, prefix=settings.API_V1_STR)

    @application.get("/", tags=["Health"])
    async def root():
        return {
            "message": f"Welcome to {settings.PROJECT_NAME}",
            "version": settings.VERSION,
        }

    @application.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok", "environment": settings.ENVIRONMENT}

    return application


app = create_application()

