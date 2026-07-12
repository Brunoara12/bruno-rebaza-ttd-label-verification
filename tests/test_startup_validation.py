import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.exceptions import VisionProviderError
from backend.app.main import create_app
from backend.app import vision_service


def openai_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        cors_allowed_origins="http://localhost:5173",
        vision_provider="openai",
        vision_model="recognized-model",
        vision_timeout_seconds=1.25,
        vision_max_image_edge_px=1280,
        vision_jpeg_quality=76,
        max_upload_bytes=1024,
        batch_max_items=2,
        batch_worker_concurrency=1,
        openai_api_key="test-key",
    )


def test_mock_startup_does_not_construct_or_validate_openai_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        vision_service,
        "OpenAIVisionService",
        lambda **_: pytest.fail("mock startup must not initialize OpenAI"),
    )
    mock_settings = openai_settings().model_copy(update={"vision_provider": "mock", "openai_api_key": None})

    with TestClient(create_app(mock_settings)):
        pass


def test_openai_startup_retrieves_configured_model_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, float]] = []

    class FakeOpenAIService:
        def __init__(self, *, model: str, timeout_seconds: float, **_: object) -> None:
            self.model = model
            self.timeout_seconds = timeout_seconds

        def validate_model(self) -> None:
            calls.append((self.model, self.timeout_seconds))

    monkeypatch.setattr(vision_service, "OpenAIVisionService", FakeOpenAIService)

    with TestClient(create_app(openai_settings())):
        pass

    assert calls == [("recognized-model", 1.25)]


def test_openai_model_validation_failure_stops_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingOpenAIService:
        def __init__(self, **_: object) -> None:
            pass

        def validate_model(self) -> None:
            raise VisionProviderError("Configured vision model could not be verified.")

    monkeypatch.setattr(vision_service, "OpenAIVisionService", FailingOpenAIService)

    with pytest.raises(VisionProviderError):
        with TestClient(create_app(openai_settings())):
            pass
