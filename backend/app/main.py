"""FastAPI application composition and startup configuration validation."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import Settings, get_settings
from backend.app.errors import register_exception_handlers
from backend.app.routes import get_vision_service_dependency, router
from backend.app.vision_service import validate_vision_model


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Validate the configured provider model before accepting application traffic."""
    validate_vision_model(app.state.settings)
    yield


def create_app(configured_settings: Settings | None = None) -> FastAPI:
    """Create the configured FastAPI application and register its HTTP components."""
    active_settings = configured_settings or get_settings()
    application = FastAPI(title="TTB Label Verification API", lifespan=lifespan)
    application.state.settings = active_settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    register_exception_handlers(application)
    application.include_router(router)
    return application


settings = get_settings()
app = create_app(settings)

__all__ = ["app", "create_app", "get_vision_service_dependency", "settings"]
