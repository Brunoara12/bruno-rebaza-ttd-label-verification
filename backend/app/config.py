from functools import lru_cache
from os import getenv

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True), override=False)

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
DEFAULT_VISION_MODEL = "gpt-5.4-mini"
DEFAULT_VISION_PROVIDER = "mock"
DEFAULT_VISION_TIMEOUT_SECONDS = 4.0
DEFAULT_VISION_MAX_IMAGE_EDGE_PX = 1600
DEFAULT_VISION_JPEG_QUALITY = 82
DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
DEFAULT_BATCH_MAX_ITEMS = 10
DEFAULT_BATCH_WORKER_CONCURRENCY = 3


class Settings:
    def __init__(self) -> None:
        self.app_env = getenv("APP_ENV", "local")
        self.cors_allowed_origins = self._parse_origins(
            getenv("CORS_ALLOWED_ORIGINS", DEFAULT_CORS_ORIGINS)
        )
        self.openai_api_key = getenv("OPENAI_API_KEY")
        self.vision_provider = getenv("VISION_PROVIDER", DEFAULT_VISION_PROVIDER).strip().lower()
        self.vision_model = getenv("VISION_MODEL", DEFAULT_VISION_MODEL)
        self.vision_timeout_seconds = self._parse_float(
            getenv("VISION_TIMEOUT_SECONDS"),
            DEFAULT_VISION_TIMEOUT_SECONDS,
        )
        self.vision_max_image_edge_px = self._parse_int(
            getenv("VISION_MAX_IMAGE_EDGE_PX"),
            DEFAULT_VISION_MAX_IMAGE_EDGE_PX,
        )
        self.vision_jpeg_quality = self._parse_int(
            getenv("VISION_JPEG_QUALITY"),
            DEFAULT_VISION_JPEG_QUALITY,
        )
        self.max_upload_bytes = self._parse_int(
            getenv("MAX_UPLOAD_BYTES"),
            DEFAULT_MAX_UPLOAD_BYTES,
        )
        self.batch_max_items = self._parse_int(
            getenv("BATCH_MAX_ITEMS"),
            DEFAULT_BATCH_MAX_ITEMS,
        )
        self.batch_worker_concurrency = self._parse_int(
            getenv("BATCH_WORKER_CONCURRENCY"),
            DEFAULT_BATCH_WORKER_CONCURRENCY,
        )

    @staticmethod
    def _parse_origins(raw_value: str) -> list[str]:
        return [origin.strip() for origin in raw_value.split(",") if origin.strip()]

    @staticmethod
    def _parse_float(raw_value: str | None, default: float) -> float:
        if raw_value is None or not raw_value.strip():
            return default
        return float(raw_value)

    @staticmethod
    def _parse_int(raw_value: str | None, default: int) -> int:
        if raw_value is None or not raw_value.strip():
            return default
        return int(raw_value)


@lru_cache
def get_settings() -> Settings:
    return Settings()

