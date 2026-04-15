from __future__ import annotations

from fastapi import FastAPI

from src.config import get_settings
from src.middleware import (
    AuthMiddleware,
    ContentTypeMiddleware,
    CorsMiddleware,
    ErrorMiddleware,
    RequestIdMiddleware,
    RequestLoggingMiddleware,
    RequestSizeMiddleware,
    ValidationMiddleware,
)
from src.router.health import health_router
from src.router.v1 import v1_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Bridge API",
        version="0.1.0",
        description="A backend for an accounting research and workflow product.",
    )

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestSizeMiddleware, settings=settings)
    app.add_middleware(CorsMiddleware, settings=settings)
    app.add_middleware(ContentTypeMiddleware, settings=settings)
    app.add_middleware(AuthMiddleware, settings=settings)
    app.add_middleware(ErrorMiddleware)
    app.add_middleware(ValidationMiddleware)

    app.include_router(health_router, prefix="/api")
    app.include_router(v1_router, prefix="/api")
    return app


app = create_app()
