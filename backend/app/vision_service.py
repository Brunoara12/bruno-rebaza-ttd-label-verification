from __future__ import annotations

import base64
import json
from typing import Any, Protocol

from pydantic import Field, ValidationError

from backend.app.config import Settings, get_settings
from backend.app.image_preprocess import PreprocessedImage
from backend.app.schemas import ExtractedLabel, StrictModel


DEFAULT_VISION_MODEL = "gpt-5.4-mini"
DEFAULT_VISION_TIMEOUT_SECONDS = 4.0
DEFAULT_MAX_OUTPUT_TOKENS = 900

EXTRACTION_PROMPT = """
Extract visible beverage alcohol label text into the requested schema fields.

Use null for any field that is unknown, unreadable, hidden, not present, or too uncertain.
Do not guess from product knowledge or complete missing text from memory. For blurry,
angled, glare-heavy, cropped, or partially readable images, return only readable fields.

The government_warning field is legally critical. Copy only visible warning-like text.
Preserve case, punctuation, spelling, wording, parentheses, and OCR-looking mistakes
exactly as visible. Do not correct, normalize, title-case, complete from memory, or
substitute the canonical government warning. If partially readable, return the readable
visible text verbatim with low confidence. If no warning-like text is readable, return null.

If the image is not a beverage alcohol label, return null for all seven label fields,
raw_text as any visible text if present, and extraction_confidence as 0.0.
""".strip()


class VisionServiceError(RuntimeError):
    """Base class for expected vision-service failures."""


class VisionTimeoutError(VisionServiceError):
    """Raised when the model call exceeds the configured timeout budget."""


class VisionParseError(VisionServiceError):
    """Raised when the model response cannot be validated as ExtractedLabel data."""


class VisionProviderError(VisionServiceError):
    """Raised for provider setup or non-timeout provider failures."""


class VisionService(Protocol):
    def extract_label(self, image: PreprocessedImage) -> ExtractedLabel:
        """Extract structured label data from a preprocessed image."""
        ...


class VisionExtractionPayload(StrictModel):
    brand_name: str | None
    class_type: str | None
    abv: str | None
    net_contents: str | None
    producer: str | None
    country_of_origin: str | None
    government_warning: str | None
    raw_text: str | None
    extraction_confidence: float = Field(ge=0.0, le=1.0)

    def to_extracted_label(self) -> ExtractedLabel:
        return ExtractedLabel(**self.model_dump())


VISION_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "brand_name": {"type": ["string", "null"]},
        "class_type": {"type": ["string", "null"]},
        "abv": {"type": ["string", "null"]},
        "net_contents": {"type": ["string", "null"]},
        "producer": {"type": ["string", "null"]},
        "country_of_origin": {"type": ["string", "null"]},
        "government_warning": {"type": ["string", "null"]},
        "raw_text": {"type": ["string", "null"]},
        "extraction_confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "required": [
        "brand_name",
        "class_type",
        "abv",
        "net_contents",
        "producer",
        "country_of_origin",
        "government_warning",
        "raw_text",
        "extraction_confidence",
    ],
    "additionalProperties": False,
}


class OpenAIVisionService:
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str = DEFAULT_VISION_MODEL,
        timeout_seconds: float = DEFAULT_VISION_TIMEOUT_SECONDS,
        client: Any | None = None,
    ) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds

        if client is not None:
            self._client = client
            return

        if not api_key:
            raise VisionProviderError("OPENAI_API_KEY is required for the OpenAI vision provider.")

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency is installed in normal envs
            raise VisionProviderError("The openai package is not installed.") from exc

        self._client = OpenAI(api_key=api_key, timeout=timeout_seconds)

    def extract_label(self, image: PreprocessedImage) -> ExtractedLabel:
        try:
            response = self._client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": "You extract structured data from beverage alcohol labels.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": EXTRACTION_PROMPT},
                            {
                                "type": "input_image",
                                "image_url": _image_data_url(image),
                                "detail": "high",
                            },
                        ],
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "extracted_label",
                        "schema": VISION_EXTRACTION_SCHEMA,
                        "strict": True,
                    }
                },
                max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
                timeout=self.timeout_seconds,
            )
        except Exception as exc:
            if _is_timeout_error(exc):
                raise VisionTimeoutError("Vision model timed out.") from exc
            raise VisionProviderError("Vision provider request failed.") from exc

        return _payload_from_response(response).to_extracted_label()


class MockVisionService:
    def __init__(self, label: ExtractedLabel | None = None) -> None:
        self._label = label or ExtractedLabel(
            brand_name="Acme Reserve",
            class_type="Straight Bourbon Whiskey",
            abv="45% Alc./Vol. (90 Proof)",
            net_contents="750 mL",
            producer="Acme Distilling Co.",
            country_of_origin="USA",
            government_warning=(
                "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL, WOMEN "
                "SHOULD NOT DRINK ALCOHOLIC BEVERAGES DURING PREGNANCY BECAUSE OF "
                "THE RISK OF BIRTH DEFECTS. (2) CONSUMPTION OF ALCOHOLIC BEVERAGES "
                "IMPAIRS YOUR ABILITY TO DRIVE A CAR OR OPERATE MACHINERY, AND MAY "
                "CAUSE HEALTH PROBLEMS."
            ),
            raw_text="Mock OCR text from a readable beverage alcohol label.",
            extraction_confidence=0.98,
        )

    def extract_label(self, image: PreprocessedImage) -> ExtractedLabel:
        return self._label.model_copy(deep=True)


def get_vision_service(settings: Settings | None = None) -> VisionService:
    settings = settings or get_settings()

    if settings.vision_provider == "mock":
        return MockVisionService()
    if settings.vision_provider == "openai":
        return OpenAIVisionService(
            api_key=settings.openai_api_key,
            model=settings.vision_model,
            timeout_seconds=settings.vision_timeout_seconds,
        )

    raise VisionProviderError(f"Unsupported VISION_PROVIDER: {settings.vision_provider}")


def _payload_from_response(response: Any) -> VisionExtractionPayload:
    _raise_for_bad_response_status(response)

    parsed = _find_parsed_payload(response)
    if parsed is None:
        output_text = _find_output_text(response)
        if not output_text:
            raise VisionParseError("Vision response did not include structured output text.")
        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise VisionParseError("Vision response was not valid JSON.") from exc

    try:
        return VisionExtractionPayload.model_validate(parsed)
    except ValidationError as exc:
        raise VisionParseError("Vision response did not match the ExtractedLabel schema.") from exc


def _raise_for_bad_response_status(response: Any) -> None:
    status = _read_value(response, "status")
    if status in {"failed", "incomplete", "cancelled"}:
        detail = _read_value(response, "error") or _read_value(response, "incomplete_details")
        raise VisionParseError(f"Vision response was {status}: {detail}")

    if _contains_refusal(response):
        raise VisionParseError("Vision response contained a refusal instead of extraction data.")


def _find_parsed_payload(response: Any) -> Any | None:
    output_parsed = _read_value(response, "output_parsed")
    if output_parsed is not None:
        return output_parsed

    for item in _as_list(_read_value(response, "output")):
        for content_part in _as_list(_read_value(item, "content")):
            parsed = _read_value(content_part, "parsed")
            if parsed is not None:
                return parsed

    return None


def _find_output_text(response: Any) -> str | None:
    output_text = _read_value(response, "output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    for item in _as_list(_read_value(response, "output")):
        for content_part in _as_list(_read_value(item, "content")):
            text = _read_value(content_part, "text")
            if isinstance(text, str) and text.strip():
                return text

    return None


def _contains_refusal(response: Any) -> bool:
    for item in _as_list(_read_value(response, "output")):
        for content_part in _as_list(_read_value(item, "content")):
            part_type = _read_value(content_part, "type")
            refusal = _read_value(content_part, "refusal")
            if part_type == "refusal" or refusal:
                return True
    return False


def _image_data_url(image: PreprocessedImage) -> str:
    encoded_image = base64.b64encode(image.data).decode("ascii")
    return f"data:{image.mime_type};base64,{encoded_image}"


def _read_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _is_timeout_error(exc: Exception) -> bool:
    timeout_names = {
        "APITimeoutError",
        "ReadTimeout",
        "Timeout",
        "TimeoutError",
        "TimeoutException",
    }
    return isinstance(exc, TimeoutError) or exc.__class__.__name__ in timeout_names
