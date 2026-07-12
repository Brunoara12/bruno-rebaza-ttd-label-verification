import math

import pytest
from pydantic import ValidationError

from backend.app.config import Settings


def settings_values(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "app_env": "test",
        "cors_allowed_origins": "http://localhost:5173, http://127.0.0.1:5173",
        "vision_provider": "mock",
        "vision_model": "test-model",
        "vision_timeout_seconds": 1.0,
        "vision_max_image_edge_px": 1280,
        "vision_jpeg_quality": 76,
        "max_upload_bytes": 1024,
        "batch_max_items": 2,
        "batch_worker_concurrency": 1,
    }
    values.update(overrides)
    return values


def test_settings_parses_csv_origins_and_normalizes_provider() -> None:
    settings = Settings(_env_file=None, **settings_values(vision_provider=" OpenAI ", openai_api_key="key"))

    assert settings.cors_allowed_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]
    assert settings.vision_provider == "openai"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("app_env", "   "),
        ("vision_model", "   "),
        ("cors_allowed_origins", " , "),
        ("vision_provider", "unknown"),
        ("vision_timeout_seconds", 0),
        ("vision_timeout_seconds", -1),
        ("vision_timeout_seconds", math.inf),
        ("vision_timeout_seconds", math.nan),
        ("vision_max_image_edge_px", 0),
        ("vision_jpeg_quality", 0),
        ("vision_jpeg_quality", 101),
        ("max_upload_bytes", 0),
        ("batch_max_items", 0),
        ("batch_worker_concurrency", 0),
    ],
)
def test_settings_rejects_invalid_configured_values(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **settings_values(**{field: value}))


def test_openai_settings_require_a_nonblank_api_key() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **settings_values(vision_provider="openai", openai_api_key="  "))


def test_settings_reject_malformed_numeric_environment_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VISION_TIMEOUT_SECONDS", "not-a-number")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_environment_values_override_dotenv_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("VISION_TIMEOUT_SECONDS=1.25\n", encoding="utf-8")
    monkeypatch.setenv("VISION_TIMEOUT_SECONDS", "2.5")

    settings = Settings(_env_file=dotenv_file)

    assert settings.vision_timeout_seconds == 2.5
