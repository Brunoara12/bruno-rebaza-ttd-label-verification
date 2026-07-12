import json
from typing import Any

import pytest

from backend.app.image_preprocess import PreprocessedImage
from backend.app.schemas import ExtractedLabel
from backend.app.vision_service import (
    EXTRACTION_PROMPT,
    MockVisionService,
    OpenAIVisionService,
    VisionParseError,
    VisionProviderError,
    VisionTimeoutError,
    DEFAULT_MAX_OUTPUT_TOKENS,
    _payload_from_response,
)


def preprocessed_image() -> PreprocessedImage:
    return PreprocessedImage(
        data=b"\xff\xd8mock-jpeg\xff\xd9",
        mime_type="image/jpeg",
        width=100,
        height=80,
    )


def label_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "brand_name": "Acme Reserve",
        "class_type": "Straight Bourbon Whiskey",
        "abv": "45% Alc./Vol. (90 Proof)",
        "net_contents": "750 mL",
        "producer": "Acme Distilling Co.",
        "country_of_origin": "USA",
        "government_warning": "GOVERNMENT WARNING: VISIBLE TEXT",
        "raw_text": "Acme Reserve GOVERNMENT WARNING: VISIBLE TEXT",
        "extraction_confidence": 0.97,
    }
    payload.update(overrides)
    return payload


class FakeResponse:
    def __init__(
        self,
        payload: dict[str, object] | None = None,
        *,
        output_text: str | None = None,
        status: str = "completed",
    ) -> None:
        self.status = status
        self.output_text = json.dumps(payload) if payload is not None else output_text


class FakeResponses:
    def __init__(self, response: object | None = None, exc: Exception | None = None) -> None:
        self.response = response
        self.exc = exc
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        if self.exc is not None:
            raise self.exc
        return self.response


class FakeClient:
    def __init__(self, response: object | None = None, exc: Exception | None = None) -> None:
        self.responses = FakeResponses(response=response, exc=exc)
        self.models = FakeModels()


class FakeModels:
    def __init__(self, exc: Exception | None = None) -> None:
        self.exc = exc
        self.calls: list[tuple[str, float]] = []

    def retrieve(self, model: str, *, timeout: float) -> object:
        self.calls.append((model, timeout))
        if self.exc is not None:
            raise self.exc
        return {"id": model}


def test_mock_vision_service_returns_deterministic_label_without_api() -> None:
    service = MockVisionService()

    first = service.extract_label(preprocessed_image())
    second = service.extract_label(preprocessed_image())

    assert first == second
    assert first.brand_name == "Acme Reserve"
    assert first.extraction_confidence == 0.98
    assert first is not second


def test_openai_service_sends_structured_schema_prompt_and_image_payload() -> None:
    client = FakeClient(response=FakeResponse(label_payload()))
    service = OpenAIVisionService(
        api_key="test-key",
        model="test-model",
        timeout_seconds=2.5,
        client=client,
    )

    result = service.extract_label(preprocessed_image())

    assert result.brand_name == "Acme Reserve"
    assert result.government_warning == "GOVERNMENT WARNING: VISIBLE TEXT"

    call = client.responses.calls[0]
    assert call["model"] == "test-model"
    assert call["timeout"] == 2.5
    assert call["max_output_tokens"] == DEFAULT_MAX_OUTPUT_TOKENS
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True
    assert call["text"]["format"]["schema"]["additionalProperties"] is False
    assert "government_warning" in call["text"]["format"]["schema"]["required"]

    user_content = call["input"][1]["content"]
    assert user_content[0]["type"] == "input_text"
    assert "Preserve case, punctuation, spelling" in user_content[0]["text"]
    assert "Do not correct, normalize, title-case" in user_content[0]["text"]
    assert user_content[1]["type"] == "input_image"
    assert user_content[1]["detail"] == "high"
    assert user_content[1]["image_url"].startswith("data:image/jpeg;base64,")


def test_openai_service_maps_timeout_to_typed_error() -> None:
    client = FakeClient(exc=TimeoutError("too slow"))
    service = OpenAIVisionService(api_key="test-key", client=client)

    with pytest.raises(VisionTimeoutError):
        service.extract_label(preprocessed_image())


def test_openai_service_retrieves_configured_model_for_startup_validation() -> None:
    client = FakeClient()
    service = OpenAIVisionService(
        api_key="test-key",
        model="test-model",
        timeout_seconds=2.5,
        client=client,
    )

    service.validate_model()

    assert client.models.calls == [("test-model", 2.5)]


def test_openai_model_validation_maps_provider_errors() -> None:
    client = FakeClient()
    client.models.exc = RuntimeError("not found")
    service = OpenAIVisionService(api_key="test-key", client=client)

    with pytest.raises(VisionProviderError):
        service.validate_model()


def test_malformed_json_maps_to_parse_error() -> None:
    client = FakeClient(response=FakeResponse(output_text="{not-json"))
    service = OpenAIVisionService(api_key="test-key", client=client)

    with pytest.raises(VisionParseError):
        service.extract_label(preprocessed_image())


def test_schema_invalid_output_maps_to_parse_error() -> None:
    invalid_payload = label_payload(extraction_confidence=1.5)
    client = FakeClient(response=FakeResponse(invalid_payload))
    service = OpenAIVisionService(api_key="test-key", client=client)

    with pytest.raises(VisionParseError):
        service.extract_label(preprocessed_image())


def test_missing_extraction_confidence_defaults_to_none() -> None:
    payload = label_payload()
    del payload["extraction_confidence"]

    result = _payload_from_response(FakeResponse(payload))

    assert result.extraction_confidence is None


def test_incomplete_or_refused_response_maps_to_parse_error() -> None:
    with pytest.raises(VisionParseError):
        _payload_from_response({"status": "incomplete", "incomplete_details": {"reason": "max_tokens"}})

    with pytest.raises(VisionParseError):
        _payload_from_response(
            {
                "status": "completed",
                "output": [{"content": [{"type": "refusal", "refusal": "no"}]}],
            }
        )


def test_non_label_image_response_returns_null_fields_and_zero_confidence() -> None:
    client = FakeClient(
        response=FakeResponse(
            label_payload(
                brand_name=None,
                class_type=None,
                abv=None,
                net_contents=None,
                producer=None,
                country_of_origin=None,
                government_warning=None,
                raw_text="SALE 20% OFF",
                extraction_confidence=0.0,
            )
        )
    )
    service = OpenAIVisionService(api_key="test-key", client=client)

    result = service.extract_label(preprocessed_image())

    assert result.brand_name is None
    assert result.government_warning is None
    assert result.raw_text == "SALE 20% OFF"
    assert result.extraction_confidence == 0.0


def test_partial_poor_image_response_returns_partial_data() -> None:
    partial = ExtractedLabel(
        brand_name="Acme",
        class_type=None,
        abv=None,
        net_contents="750 mL",
        producer=None,
        country_of_origin=None,
        government_warning="GOVERNMENT WARNING: PARTIAL",
        raw_text="Acme 750 mL GOVERNMENT WARNING: PARTIAL",
        extraction_confidence=0.35,
    )
    service = MockVisionService(partial)

    result = service.extract_label(preprocessed_image())

    assert result.brand_name == "Acme"
    assert result.class_type is None
    assert result.net_contents == "750 mL"
    assert result.extraction_confidence == 0.35


def test_prompt_contains_non_label_and_unknown_null_rules() -> None:
    assert "Use null for any field" in EXTRACTION_PROMPT
    assert "If the image is not a beverage alcohol label" in EXTRACTION_PROMPT


def test_strict_schema_is_derived_from_extracted_label_and_allows_null_confidence() -> None:
    from backend.app.vision_service import VISION_EXTRACTION_SCHEMA

    assert VISION_EXTRACTION_SCHEMA["additionalProperties"] is False
    assert set(VISION_EXTRACTION_SCHEMA["required"]) == set(VISION_EXTRACTION_SCHEMA["properties"])
    confidence_schema = VISION_EXTRACTION_SCHEMA["properties"]["extraction_confidence"]
    assert {entry["type"] for entry in confidence_schema["anyOf"]} == {"number", "null"}
