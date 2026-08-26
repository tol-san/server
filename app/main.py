from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.profiles.router import router as profiles_router
from app.users.router import router as users_router


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
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

