import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.chats.router import router as chats_router
from app.comments.router import router as comments_router
from app.communities.router import router as communities_router
from app.core import close_meilisearch, init_meilisearch_indexes
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.observability import ObservabilityMiddleware, configure_logging, metrics_endpoint
from app.core.redis import close_redis
from app.feeds.router import router as feeds_router
from app.interests.router import router as interests_router
from app.live_rooms.router import router as live_rooms_router
from app.notifications.router import router as notifications_router
from app.posts.router import router as posts_router
from app.profiles.router import router as profiles_router
from app.recommendations.router import router as recommendations_router
from app.reports.router import router as reports_router
from app.saved_posts.router import router as saved_posts_router
from app.search.router import router as search_router
from app.users.router import router as users_router

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Background worker instances (lazy import to avoid circular deps)
# ─────────────────────────────────────────────────────────────────────────────
_worker_tasks: list[asyncio.Task] = []


def _create_worker_tasks() -> list[asyncio.Task]:
    from app.workers.outbox_relay import outbox_relay_worker
    from app.workers.notification_worker import chat_notification_worker, live_notification_worker
    from app.workers.analytics_worker import chat_analytics_worker, live_analytics_worker
    from app.workers.moderation_worker import moderation_worker

    workers = [
        outbox_relay_worker,
        chat_notification_worker,
        live_notification_worker,
        chat_analytics_worker,
        live_analytics_worker,
        moderation_worker,
    ]
    return [
        asyncio.create_task(w.start(), name=getattr(w, "worker_name", type(w).__name__))
        for w in workers
    ]

def _on_worker_done(task: asyncio.Task) -> None:
    """Log unexpected worker termination."""
    if task.cancelled():
        return
    exc = task.exception() if not task.cancelled() else None
    if exc is not None:
        logger.error(
            "Background worker '%s' crashed unexpectedly: %s",
            task.get_name(),
            exc,
            exc_info=exc,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure structured logging
    configure_logging()

    # Startup
    try:
        await init_meilisearch_indexes()
    except Exception as exc:
        logger.warning("Meilisearch initial setup warning: %s", exc)

    # Start background workers
    tasks = _create_worker_tasks()
    _worker_tasks.extend(tasks)
    
    for task in tasks:
        task.add_done_callback(_on_worker_done)
        
    logger.info("Started %d background workers", len(tasks))

    yield

    # Shutdown — cancel workers gracefully
    for task in _worker_tasks:
        task.cancel()
    if _worker_tasks:
        await asyncio.gather(*_worker_tasks, return_exceptions=True)
    _worker_tasks.clear()
    logger.info("Background workers stopped")

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
    origins = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS] if settings.BACKEND_CORS_ORIGINS else []
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins else ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Observability middleware (trace ID, HTTP metrics)
    if settings.ENABLE_METRICS:
        application.add_middleware(ObservabilityMiddleware)

    # Register custom exception handlers
    register_exception_handlers(application)

    # Prometheus metrics endpoint
    if settings.ENABLE_METRICS:
        import os
        async def protected_metrics_endpoint(request: Request):
            api_key = os.environ.get("METRICS_API_KEY", "")
            if api_key:
                token = request.headers.get("X-Metrics-Token", "")
                if token != api_key:
                    from fastapi.responses import Response as FastAPIResponse
                    return FastAPIResponse(status_code=403, content="Forbidden")
            return await metrics_endpoint(request)
        application.add_route("/metrics", protected_metrics_endpoint, methods=["GET"])

    # Include routers
    application.include_router(auth_router, prefix=settings.API_V1_STR)
    application.include_router(users_router, prefix=settings.API_V1_STR)
    application.include_router(profiles_router, prefix=settings.API_V1_STR)
    application.include_router(interests_router, prefix=settings.API_V1_STR)
    application.include_router(communities_router, prefix=settings.API_V1_STR)
    application.include_router(posts_router, prefix=settings.API_V1_STR)
    application.include_router(comments_router, prefix=settings.API_V1_STR)
    application.include_router(saved_posts_router, prefix=settings.API_V1_STR)
    application.include_router(feeds_router, prefix=settings.API_V1_STR)
    application.include_router(recommendations_router, prefix=settings.API_V1_STR)
    application.include_router(search_router, prefix=settings.API_V1_STR)
    application.include_router(notifications_router, prefix=settings.API_V1_STR)
    application.include_router(reports_router, prefix=settings.API_V1_STR)
    application.include_router(chats_router, prefix=settings.API_V1_STR)
    application.include_router(live_rooms_router, prefix=settings.API_V1_STR)

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

