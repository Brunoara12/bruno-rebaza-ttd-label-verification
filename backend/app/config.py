from functools import lru_cache
from os import getenv

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


class Settings:
    def __init__(self) -> None:
        self.app_env = getenv("APP_ENV", "local")
        self.cors_allowed_origins = self._parse_origins(
            getenv("CORS_ALLOWED_ORIGINS", DEFAULT_CORS_ORIGINS)
        )

    @staticmethod
    def _parse_origins(raw_value: str) -> list[str]:
        return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

