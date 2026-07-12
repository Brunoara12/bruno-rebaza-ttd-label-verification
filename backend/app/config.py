"""Validated environment-backed application configuration."""

from functools import lru_cache
from typing import Annotated, Literal

from dotenv import find_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
DEFAULT_VISION_MODEL = "gpt-5.4-mini"
DEFAULT_VISION_PROVIDER = "mock"
DEFAULT_VISION_TIMEOUT_SECONDS = 4.0
DEFAULT_VISION_MAX_IMAGE_EDGE_PX = 1280
DEFAULT_VISION_JPEG_QUALITY = 76
DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
DEFAULT_BATCH_MAX_ITEMS = 10
DEFAULT_BATCH_WORKER_CONCURRENCY = 3


DOTENV_PATH = find_dotenv(usecwd=True) or ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables and the local dotenv file."""

    model_config = SettingsConfigDict(
        env_file=DOTENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="local", min_length=1)
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: DEFAULT_CORS_ORIGINS.split(",")
    )
    openai_api_key: str | None = None
    vision_provider: Literal["mock", "openai"] = DEFAULT_VISION_PROVIDER
    vision_model: str = Field(default=DEFAULT_VISION_MODEL, min_length=1)
    vision_timeout_seconds: float = Field(
        default=DEFAULT_VISION_TIMEOUT_SECONDS,
        gt=0,
        allow_inf_nan=False,
    )
    vision_max_image_edge_px: int = Field(default=DEFAULT_VISION_MAX_IMAGE_EDGE_PX, gt=0)
    vision_jpeg_quality: int = Field(default=DEFAULT_VISION_JPEG_QUALITY, ge=1, le=100)
    max_upload_bytes: int = Field(default=DEFAULT_MAX_UPLOAD_BYTES, gt=0)
    batch_max_items: int = Field(default=DEFAULT_BATCH_MAX_ITEMS, gt=0)
    batch_worker_concurrency: int = Field(default=DEFAULT_BATCH_WORKER_CONCURRENCY, gt=0)

    @field_validator("app_env", "vision_model", mode="before")
    @classmethod
    def _strip_required_text(cls, value: object) -> str:
        normalized = value.strip() if isinstance(value, str) else ""
        if not normalized:
            raise ValueError("must be a non-empty string")
        return normalized

    @field_validator("vision_provider", mode="before")
    @classmethod
    def _normalize_provider(cls, value: object) -> str:
        return value.strip().lower() if isinstance(value, str) else ""

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _parse_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list):
            return [origin.strip() for origin in value if isinstance(origin, str) and origin.strip()]
        return []

    @field_validator("cors_allowed_origins")
    @classmethod
    def _require_origins(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("must include at least one origin")
        return value

    @model_validator(mode="after")
    def _require_openai_key(self) -> "Settings":
        if self.vision_provider == "openai" and not (self.openai_api_key or "").strip():
            raise ValueError("OPENAI_API_KEY is required when VISION_PROVIDER=openai")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached validated application settings."""
    return Settings()

