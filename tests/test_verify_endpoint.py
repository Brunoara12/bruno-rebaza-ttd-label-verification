from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.image_preprocess import PreprocessedImage
from backend.app.main import app, get_vision_service_dependency, settings
from backend.app.schemas import ExtractedLabel
from backend.app.vision_service import VisionParseError, VisionProviderError, VisionTimeoutError


CANONICAL_WARNING = (
    "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL, WOMEN "
    "SHOULD NOT DRINK ALCOHOLIC BEVERAGES DURING PREGNANCY BECAUSE OF "
    "THE RISK OF BIRTH DEFECTS. (2) CONSUMPTION OF ALCOHOLIC BEVERAGES "
    "IMPAIRS YOUR ABILITY TO DRIVE A CAR OR OPERATE MACHINERY, AND MAY "
    "CAUSE HEALTH PROBLEMS."
)


class RecordingVisionService:
    def __init__(self, label: ExtractedLabel | None = None, exc: Exception | None = None) -> None:
        self.label = label or extracted_label()
        self.exc = exc
        self.images: list[PreprocessedImage] = []

    def extract_label(self, image: PreprocessedImage) -> ExtractedLabel:
        self.images.append(image)
        if self.exc is not None:
            raise self.exc
        return self.label


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()


def image_bytes(image_format: str = "PNG") -> bytes:
    image = Image.new("RGB", (80, 60), color=(150, 40, 40))
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def application_form(**overrides: str) -> dict[str, str]:
    values = {
        "brand_name": "Acme Reserve",
        "class_type": "Straight Bourbon Whiskey",
        "abv": "45%",
        "net_contents": "750 mL",
        "producer": "Acme Distilling Co.",
        "country_of_origin": "United States",
        "government_warning": CANONICAL_WARNING,
    }
    values.update(overrides)
    return values


def extracted_label(**overrides: object) -> ExtractedLabel:
    values = {
        "brand_name": "Acme Reserve",
        "class_type": "Straight Bourbon Whiskey",
        "abv": "45% Alc./Vol. (90 Proof)",
        "net_contents": "750ml",
        "producer": "Acme Distilling Co.",
        "country_of_origin": "USA",
        "government_warning": CANONICAL_WARNING,
        "raw_text": "Acme Reserve label text",
        "extraction_confidence": 0.97,
    }
    values.update(overrides)
    return ExtractedLabel(**values)


def verify_files(
    content: bytes | None = None,
    filename: str = "label.png",
    content_type: str = "image/png",
) -> dict[str, tuple[str, bytes, str]]:
    return {"image": (filename, image_bytes() if content is None else content, content_type)}


def override_vision_service(service: RecordingVisionService) -> None:
    app.dependency_overrides[get_vision_service_dependency] = lambda: service


def test_verify_returns_full_verification_result_with_preprocessed_image(client: TestClient) -> None:
    service = RecordingVisionService()
    override_vision_service(service)

    response = client.post("/verify", data=application_form(), files=verify_files())

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_verdict"] == "APPROVED"
    assert payload["latency_ms"] >= 0
    assert response.headers["x-verification-latency-ms"] == str(payload["latency_ms"])
    assert [field_result["field"] for field_result in payload["results"]] == [
        "brand_name",
        "class_type",
        "abv",
        "net_contents",
        "producer",
        "country_of_origin",
        "government_warning",
    ]
    assert {field_result["status"] for field_result in payload["results"]} == {"PASS"}
    assert payload["results"][0]["expected"] == "Acme Reserve"
    assert payload["results"][0]["found"] == "Acme Reserve"

    assert len(service.images) == 1
    assert service.images[0].mime_type == "image/jpeg"
    assert service.images[0].data.startswith(b"\xff\xd8")


def test_warning_mismatch_surfaces_extracted_warning_text(client: TestClient) -> None:
    extracted_warning = CANONICAL_WARNING.title()
    service = RecordingVisionService(extracted_label(government_warning=extracted_warning))
    override_vision_service(service)

    response = client.post("/verify", data=application_form(), files=verify_files())

    assert response.status_code == 200
    payload = response.json()
    warning_result = payload["results"][-1]
    assert payload["overall_verdict"] == "NEEDS_REVIEW"
    assert warning_result["field"] == "government_warning"
    assert warning_result["status"] == "FAIL"
    assert warning_result["expected"] == CANONICAL_WARNING
    assert warning_result["found"] == extracted_warning


def test_empty_submission_returns_readable_422(client: TestClient) -> None:
    response = client.post("/verify")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert "image" in {field["field"] for field in payload["error"]["fields"]}
    assert "stack" not in response.text.lower()
    assert "traceback" not in response.text.lower()


def test_missing_image_returns_readable_422(client: TestClient) -> None:
    response = client.post("/verify", data=application_form())

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["fields"][0]["field"] == "image"


def test_missing_required_field_returns_readable_422(client: TestClient) -> None:
    data = application_form()
    del data["brand_name"]

    response = client.post("/verify", data=data, files=verify_files())

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert "brand_name" in {field["field"] for field in payload["error"]["fields"]}


def test_blank_required_field_returns_readable_422(client: TestClient) -> None:
    response = client.post(
        "/verify",
        data=application_form(brand_name="   "),
        files=verify_files(),
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["fields"][0]["field"] == "brand_name"
    assert payload["error"]["fields"][0]["message"] == "Please provide brand name."


def test_unsupported_mime_type_returns_readable_422(client: TestClient) -> None:
    response = client.post(
        "/verify",
        data=application_form(),
        files=verify_files(b"plain text", "label.txt", "text/plain"),
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    assert payload["error"]["fields"][0]["field"] == "image"
    assert "JPEG" in payload["error"]["message"]


def test_oversized_upload_returns_readable_413(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "max_upload_bytes", 8)

    response = client.post(
        "/verify",
        data=application_form(),
        files=verify_files(b"123456789", "label.png", "image/png"),
    )

    assert response.status_code == 413
    payload = response.json()
    assert payload["error"]["code"] == "FILE_TOO_LARGE"
    assert payload["error"]["fields"][0]["field"] == "image"


def test_empty_file_returns_readable_400(client: TestClient) -> None:
    response = client.post(
        "/verify",
        data=application_form(),
        files=verify_files(b"", "label.png", "image/png"),
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "EMPTY_IMAGE"
    assert payload["error"]["fields"][0]["field"] == "image"


def test_corrupt_image_returns_readable_400(client: TestClient) -> None:
    response = client.post(
        "/verify",
        data=application_form(),
        files=verify_files(b"not really a png", "label.png", "image/png"),
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "INVALID_IMAGE"
    assert payload["error"]["fields"][0]["field"] == "image"
    assert "traceback" not in response.text.lower()


def test_vision_timeout_returns_needs_review_result_not_504(client: TestClient) -> None:
    service = RecordingVisionService(exc=VisionTimeoutError("too slow"))
    override_vision_service(service)

    response = client.post("/verify", data=application_form(), files=verify_files())

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_verdict"] == "NEEDS_REVIEW"
    assert {field["status"] for field in payload["results"]} == {"FAIL"}
    assert {field["reason_code"] for field in payload["results"]} == {"MODEL_TIMEOUT"}


def test_vision_parse_error_returns_needs_review_result(client: TestClient) -> None:
    service = RecordingVisionService(exc=VisionParseError("bad json"))
    override_vision_service(service)

    response = client.post("/verify", data=application_form(), files=verify_files())

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_verdict"] == "NEEDS_REVIEW"
    assert {field["reason_code"] for field in payload["results"]} == {"PARSE_ERROR"}


def test_vision_provider_error_returns_readable_502(client: TestClient) -> None:
    service = RecordingVisionService(exc=VisionProviderError("provider down"))
    override_vision_service(service)

    response = client.post("/verify", data=application_form(), files=verify_files())

    assert response.status_code == 502
    payload = response.json()
    assert payload["error"]["code"] == "VISION_PROVIDER_ERROR"
    assert "traceback" not in response.text.lower()


def test_unexpected_error_returns_readable_500() -> None:
    service = RecordingVisionService(exc=RuntimeError("boom"))
    override_vision_service(service)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/verify", data=application_form(), files=verify_files())

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "boom" not in response.text
    assert "traceback" not in response.text.lower()
    app.dependency_overrides.clear()


def test_latency_over_sla_is_returned_and_logged(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = RecordingVisionService()
    override_vision_service(service)
    readings = iter([0.0, 5.001])
    monkeypatch.setattr("backend.app.main.perf_counter", lambda: next(readings))

    with caplog.at_level("WARNING", logger="backend.app.main"):
        response = client.post("/verify", data=application_form(), files=verify_files())

    assert response.status_code == 200
    payload = response.json()
    assert payload["latency_ms"] == 5001
    assert response.headers["x-verification-latency-ms"] == "5001"
    record = next(record for record in caplog.records if record.message == "Verification completed.")
    assert record.latency_ms == 5001
    assert record.overall_verdict == "APPROVED"
    assert record.sla_exceeded is True


def test_cors_preflight_allows_verify_post(client: TestClient) -> None:
    response = client.options(
        "/verify",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
