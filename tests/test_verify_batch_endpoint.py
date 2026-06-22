import json
import threading
import time
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.image_preprocess import PreprocessedImage
from backend.app.main import app, get_vision_service_dependency, settings
from backend.app.schemas import ExtractedLabel
from backend.app.vision_service import VisionTimeoutError


CANONICAL_WARNING = (
    "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL, WOMEN "
    "SHOULD NOT DRINK ALCOHOLIC BEVERAGES DURING PREGNANCY BECAUSE OF "
    "THE RISK OF BIRTH DEFECTS. (2) CONSUMPTION OF ALCOHOLIC BEVERAGES "
    "IMPAIRS YOUR ABILITY TO DRIVE A CAR OR OPERATE MACHINERY, AND MAY "
    "CAUSE HEALTH PROBLEMS."
)


class SequenceVisionService:
    def __init__(self, responses: list[ExtractedLabel | Exception]) -> None:
        self._responses = responses
        self._lock = threading.Lock()
        self.images: list[PreprocessedImage] = []

    def extract_label(self, image: PreprocessedImage) -> ExtractedLabel:
        with self._lock:
            call_index = len(self.images)
            self.images.append(image)
            response = self._responses[min(call_index, len(self._responses) - 1)]

        if isinstance(response, Exception):
            raise response
        return response


class SlowVisionService:
    def __init__(self, delay_seconds: float = 0.05) -> None:
        self.delay_seconds = delay_seconds
        self.active_calls = 0
        self.max_active_calls = 0
        self.total_calls = 0
        self._lock = threading.Lock()

    def extract_label(self, image: PreprocessedImage) -> ExtractedLabel:
        with self._lock:
            self.active_calls += 1
            self.total_calls += 1
            self.max_active_calls = max(self.max_active_calls, self.active_calls)

        try:
            time.sleep(self.delay_seconds)
            return extracted_label()
        finally:
            with self._lock:
                self.active_calls -= 1


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


def application_values(**overrides: str) -> dict[str, str]:
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


def batch_items(count: int, overrides_by_index: dict[int, dict[str, str]] | None = None) -> list[dict]:
    overrides_by_index = overrides_by_index or {}
    return [
        {
            "client_id": f"label-{index + 1}",
            **application_values(**overrides_by_index.get(index, {})),
        }
        for index in range(count)
    ]


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


def batch_files(
    count: int,
    corrupt_indexes: set[int] | None = None,
) -> list[tuple[str, tuple[str, bytes, str]]]:
    corrupt_indexes = corrupt_indexes or set()
    files = []
    for index in range(count):
        content = b"not really a png" if index in corrupt_indexes else image_bytes()
        files.append(("images", (f"label-{index + 1}.png", content, "image/png")))
    return files


def override_vision_service(service: object) -> None:
    app.dependency_overrides[get_vision_service_dependency] = lambda: service


def post_batch(
    client: TestClient,
    items: list[dict],
    files: list[tuple[str, tuple[str, bytes, str]]] | None = None,
):
    return client.post(
        "/verify/batch",
        data={"items_json": json.dumps(items)},
        files=files if files is not None else batch_files(len(items)),
    )


def test_batch_returns_ordered_item_results_and_summary(client: TestClient) -> None:
    service = SequenceVisionService([extracted_label()])
    override_vision_service(service)

    response = post_batch(client, batch_items(3))

    assert response.status_code == 200
    payload = response.json()
    assert response.headers["x-batch-verification-latency-ms"] == str(payload["latency_ms"])
    assert payload["summary"] == {"passed": 3, "needs_review": 0, "total": 3}
    assert [item["client_id"] for item in payload["items"]] == ["label-1", "label-2", "label-3"]
    assert [item["index"] for item in payload["items"]] == [0, 1, 2]
    assert {item["status"] for item in payload["items"]} == {"COMPLETED"}
    assert {item["result"]["overall_verdict"] for item in payload["items"]} == {"APPROVED"}
    assert len(service.images) == 3


def test_batch_summary_counts_needs_review_items(client: TestClient) -> None:
    service = SequenceVisionService([extracted_label()])
    override_vision_service(service)
    items = batch_items(3, {1: {"brand_name": "Wrong Brand"}})

    response = post_batch(client, items)

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {"passed": 2, "needs_review": 1, "total": 3}
    second_item = payload["items"][1]
    assert second_item["status"] == "COMPLETED"
    assert second_item["result"]["overall_verdict"] == "NEEDS_REVIEW"
    assert second_item["error"] is None


def test_batch_item_error_does_not_abort_whole_batch(client: TestClient) -> None:
    service = SequenceVisionService([extracted_label()])
    override_vision_service(service)

    response = post_batch(client, batch_items(3), batch_files(3, corrupt_indexes={1}))

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {"passed": 2, "needs_review": 1, "total": 3}
    assert payload["items"][0]["result"]["overall_verdict"] == "APPROVED"
    assert payload["items"][1]["status"] == "ERROR"
    assert payload["items"][1]["result"] is None
    assert payload["items"][1]["error"]["code"] == "INVALID_IMAGE"
    assert payload["items"][2]["result"]["overall_verdict"] == "APPROVED"
    assert "traceback" not in response.text.lower()


def test_batch_timeout_returns_item_level_needs_review_result(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "batch_worker_concurrency", 1)
    service = SequenceVisionService(
        [
            extracted_label(),
            VisionTimeoutError("too slow"),
            extracted_label(),
        ]
    )
    override_vision_service(service)

    response = post_batch(client, batch_items(3))

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {"passed": 2, "needs_review": 1, "total": 3}
    timeout_item = payload["items"][1]
    assert timeout_item["status"] == "COMPLETED"
    assert timeout_item["result"]["overall_verdict"] == "NEEDS_REVIEW"
    assert {field["reason_code"] for field in timeout_item["result"]["results"]} == {
        "MODEL_TIMEOUT"
    }


def test_batch_invalid_json_returns_readable_422(client: TestClient) -> None:
    response = client.post(
        "/verify/batch",
        data={"items_json": "not json"},
        files=batch_files(1),
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["fields"][0]["field"] == "items_json"


def test_batch_image_count_mismatch_returns_readable_422(client: TestClient) -> None:
    response = post_batch(client, batch_items(2), batch_files(1))

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["fields"][0]["field"] == "images"


def test_batch_concurrency_is_bounded(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "batch_worker_concurrency", 2)
    monkeypatch.setattr(settings, "batch_max_items", 5)
    service = SlowVisionService()
    override_vision_service(service)

    response = post_batch(client, batch_items(5))

    assert response.status_code == 200
    assert response.json()["summary"] == {"passed": 5, "needs_review": 0, "total": 5}
    assert service.total_calls == 5
    assert service.max_active_calls == 2
