import asyncio
import json
import logging
from json import JSONDecodeError
from time import perf_counter
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.comparison import compare_label
from backend.app.config import get_settings
from backend.app.image_preprocess import ImagePreprocessError, preprocess_image
from backend.app.schemas import (
    ApplicationData,
    BatchItemResult,
    BatchSummary,
    BatchVerificationResult,
    ErrorField,
    FieldResult,
    ItemError,
    VerificationResult,
)
from backend.app.vision_service import (
    VisionParseError,
    VisionProviderError,
    VisionService,
    VisionTimeoutError,
    get_vision_service,
)

settings = get_settings()
logger = logging.getLogger(__name__)

ACCEPTED_IMAGE_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
APPLICATION_FIELD_ORDER = [
    "brand_name",
    "class_type",
    "abv",
    "net_contents",
    "producer",
    "country_of_origin",
    "government_warning",
]
FIELD_MATCH_TYPES = {
    "brand_name": "fuzzy",
    "class_type": "fuzzy",
    "abv": "numeric-normalized",
    "net_contents": "unit-normalized",
    "producer": "fuzzy",
    "country_of_origin": "country-synonym",
    "government_warning": "exact",
}
SINGLE_LABEL_SLA_MS = 5000

app = FastAPI(title="TTB Label Verification API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: list[dict[str, str]] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = fields or []


def get_vision_service_dependency() -> VisionService:
    return get_vision_service(settings)


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return _error_response(exc.status_code, exc.code, exc.message, exc.fields)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return _error_response(
        422,
        "VALIDATION_ERROR",
        "Please provide an image and all required application fields.",
        _request_validation_fields(exc),
    )


@app.exception_handler(VisionProviderError)
async def vision_provider_error_handler(_: Request, exc: VisionProviderError) -> JSONResponse:
    logger.error("Vision provider unavailable.", extra={"error_code": "VISION_PROVIDER_ERROR"})
    return _error_response(
        502,
        "VISION_PROVIDER_ERROR",
        "The vision service is unavailable. Please try again later.",
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = "The requested endpoint was not found."
    if exc.status_code != 404 and exc.detail:
        message = str(exc.detail)

    return _error_response(exc.status_code, "HTTP_ERROR", message)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, _: Exception) -> JSONResponse:
    logger.error(
        "Unhandled server error.",
        extra={"error_code": "UNHANDLED_SERVER_ERROR", "path": request.url.path},
    )
    return _error_response(
        500,
        "INTERNAL_SERVER_ERROR",
        "Something went wrong while verifying the label. Please try again.",
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ttb-label-verification-api"}


@app.post("/verify", response_model=VerificationResult)
async def verify_label(
    response: Response,
    image: UploadFile = File(...),
    brand_name: str = Form(...),
    class_type: str = Form(...),
    abv: str = Form(...),
    net_contents: str = Form(...),
    producer: str = Form(...),
    country_of_origin: str = Form(...),
    government_warning: str = Form(...),
    vision_service: VisionService = Depends(get_vision_service_dependency),
) -> VerificationResult:
    started_at = perf_counter()
    application = _application_data_from_form(
        brand_name=brand_name,
        class_type=class_type,
        abv=abv,
        net_contents=net_contents,
        producer=producer,
        country_of_origin=country_of_origin,
        government_warning=government_warning,
    )
    result = await _verify_single_upload(application, image, vision_service, started_at)
    _finalize_verification_response(response, result)
    return result


@app.post("/verify/batch", response_model=BatchVerificationResult)
async def verify_label_batch(
    response: Response,
    items_json: str = Form(...),
    images: list[UploadFile] = File(...),
    vision_service: VisionService = Depends(get_vision_service_dependency),
) -> BatchVerificationResult:
    started_at = perf_counter()
    batch_items = _batch_items_from_json(items_json)
    _validate_batch_size(batch_items)
    _validate_batch_image_count(batch_items, images)

    worker_count = max(1, settings.batch_worker_concurrency)
    semaphore = asyncio.Semaphore(worker_count)

    async def verify_batch_item(index: int, raw_item: dict[str, Any]) -> BatchItemResult:
        async with semaphore:
            return await _verify_batch_item(index, raw_item, images[index], vision_service)

    item_results = await asyncio.gather(
        *[
            verify_batch_item(index, raw_item)
            for index, raw_item in enumerate(batch_items)
        ]
    )
    result = BatchVerificationResult(
        items=item_results,
        summary=_batch_summary(item_results),
        latency_ms=_elapsed_ms(started_at),
    )
    response.headers["X-Batch-Verification-Latency-ms"] = str(result.latency_ms)
    _log_batch_result(result, worker_count)
    return result


def _application_data_from_form(**raw_fields: str) -> ApplicationData:
    blank_fields = [
        field_name
        for field_name, value in raw_fields.items()
        if not isinstance(value, str) or not value.strip()
    ]
    if blank_fields:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "Please complete all required application fields.",
            [
                _field_error(
                    field_name,
                    "REQUIRED_FIELD",
                    f"Please provide {field_name.replace('_', ' ')}.",
                )
                for field_name in blank_fields
            ],
        )

    try:
        return ApplicationData(**{key: value.strip() for key, value in raw_fields.items()})
    except ValidationError as exc:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "Please complete all required application fields.",
            _pydantic_validation_fields(exc),
        ) from exc


async def _verify_single_upload(
    application: ApplicationData,
    image: UploadFile,
    vision_service: VisionService,
    started_at: float,
) -> VerificationResult:
    _validate_upload_content_type(image)
    image_bytes = await _read_upload_bytes(image)

    try:
        preprocessed_image = preprocess_image(
            image_bytes,
            max_edge_px=settings.vision_max_image_edge_px,
            jpeg_quality=settings.vision_jpeg_quality,
        )
    except ImagePreprocessError as exc:
        raise ApiError(
            400,
            "INVALID_IMAGE",
            "The image could not be read. Please upload a clear JPEG, PNG, or WEBP image.",
            [
                _field_error(
                    "image",
                    "INVALID_IMAGE",
                    "The image file is corrupt or unsupported.",
                )
            ],
        ) from exc

    try:
        extracted_label = await asyncio.to_thread(
            vision_service.extract_label,
            preprocessed_image,
        )
    except VisionTimeoutError:
        return _failed_verification_result(
            application,
            "MODEL_TIMEOUT",
            _elapsed_ms(started_at),
        )
    except VisionParseError:
        return _failed_verification_result(
            application,
            "PARSE_ERROR",
            _elapsed_ms(started_at),
        )

    result = compare_label(application, extracted_label)
    return result.model_copy(update={"latency_ms": _elapsed_ms(started_at)})


def _batch_items_from_json(items_json: str) -> list[dict[str, Any]]:
    try:
        batch_items = json.loads(items_json)
    except JSONDecodeError as exc:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "Please provide readable batch label details.",
            [
                _field_error(
                    "items_json",
                    "INVALID_JSON",
                    "The batch details could not be read.",
                )
            ],
        ) from exc

    if not isinstance(batch_items, list):
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "Please provide one set of label details for each image.",
            [
                _field_error(
                    "items_json",
                    "INVALID_BATCH",
                    "Batch details must be a list.",
                )
            ],
        )

    return batch_items


def _validate_batch_size(batch_items: list[dict[str, Any]]) -> None:
    if not batch_items:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "Please add at least one label to the batch.",
            [
                _field_error(
                    "items_json",
                    "EMPTY_BATCH",
                    "The batch must include at least one label.",
                )
            ],
        )

    if len(batch_items) > settings.batch_max_items:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            f"Please check no more than {settings.batch_max_items} labels at once.",
            [
                _field_error(
                    "items_json",
                    "TOO_MANY_ITEMS",
                    f"The batch has more than {settings.batch_max_items} labels.",
                )
            ],
        )


def _validate_batch_image_count(
    batch_items: list[dict[str, Any]],
    images: list[UploadFile],
) -> None:
    if len(images) != len(batch_items):
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "Please provide one image for each label in the batch.",
            [
                _field_error(
                    "images",
                    "BATCH_IMAGE_COUNT_MISMATCH",
                    "The number of images must match the number of label detail rows.",
                )
            ],
        )


async def _verify_batch_item(
    index: int,
    raw_item: dict[str, Any],
    image: UploadFile,
    vision_service: VisionService,
) -> BatchItemResult:
    client_id = _batch_item_client_id(raw_item, index)
    filename = image.filename or None
    started_at = perf_counter()

    if not isinstance(raw_item, dict):
        return _batch_item_error_result(
            index,
            client_id,
            filename,
            ApiError(
                422,
                "VALIDATION_ERROR",
                "Please provide label details for this item.",
                [
                    _field_error(
                        "item",
                        "INVALID_ITEM",
                        "This batch item must be a set of label details.",
                    )
                ],
            ),
        )

    try:
        application = _application_data_from_form(
            **{
                field_name: raw_item.get(field_name, "")
                for field_name in APPLICATION_FIELD_ORDER
            }
        )
        result = await _verify_single_upload(application, image, vision_service, started_at)
        return BatchItemResult(
            client_id=client_id,
            index=index,
            filename=filename,
            status="COMPLETED",
            result=result,
            error=None,
        )
    except ApiError as exc:
        return _batch_item_error_result(index, client_id, filename, exc)
    except VisionProviderError as exc:
        logger.error(
            "Vision provider unavailable for batch item.",
            extra={
                "error_code": "VISION_PROVIDER_ERROR",
                "batch_item_index": index,
            },
        )
        return _batch_item_error_result(
            index,
            client_id,
            filename,
            ApiError(
                502,
                "VISION_PROVIDER_ERROR",
                "The label checker is not available right now. Please try again.",
            ),
        )
    except Exception as exc:
        logger.error(
            "Unexpected batch item error.",
            extra={
                "error_code": "BATCH_ITEM_ERROR",
                "batch_item_index": index,
                "exception_type": exc.__class__.__name__,
            },
        )
        return _batch_item_error_result(
            index,
            client_id,
            filename,
            ApiError(
                500,
                "INTERNAL_SERVER_ERROR",
                "Something went wrong while checking this label. Please try again.",
            ),
        )


def _batch_item_client_id(raw_item: Any, index: int) -> str:
    if isinstance(raw_item, dict):
        client_id = raw_item.get("client_id")
        if isinstance(client_id, str) and client_id.strip():
            return client_id.strip()

    return f"item-{index + 1}"


def _batch_item_error_result(
    index: int,
    client_id: str,
    filename: str | None,
    error: ApiError,
) -> BatchItemResult:
    return BatchItemResult(
        client_id=client_id,
        index=index,
        filename=filename,
        status="ERROR",
        result=None,
        error=ItemError(
            code=error.code,
            message=error.message,
            fields=[ErrorField(**field) for field in error.fields],
        ),
    )


def _batch_summary(item_results: list[BatchItemResult]) -> BatchSummary:
    passed = sum(
        1
        for item in item_results
        if item.result is not None and item.result.overall_verdict == "APPROVED"
    )
    total = len(item_results)
    return BatchSummary(
        passed=passed,
        needs_review=total - passed,
        total=total,
    )


def _validate_upload_content_type(upload_file: UploadFile) -> None:
    if upload_file.content_type not in ACCEPTED_IMAGE_MIME_TYPES:
        raise ApiError(
            422,
            "UNSUPPORTED_FILE_TYPE",
            "Please upload a JPEG, PNG, or WEBP image.",
            [
                _field_error(
                    "image",
                    "UNSUPPORTED_FILE_TYPE",
                    "Accepted image types are JPEG, PNG, and WEBP.",
                )
            ],
        )


async def _read_upload_bytes(upload_file: UploadFile) -> bytes:
    upload_limit = settings.max_upload_bytes
    image_bytes = await upload_file.read(upload_limit + 1)

    if len(image_bytes) > upload_limit:
        raise ApiError(
            413,
            "FILE_TOO_LARGE",
            f"Please upload an image smaller than {_format_bytes(upload_limit)}.",
            [
                _field_error(
                    "image",
                    "FILE_TOO_LARGE",
                    f"The image is larger than {_format_bytes(upload_limit)}.",
                )
            ],
        )

    if not image_bytes:
        raise ApiError(
            400,
            "EMPTY_IMAGE",
            "The image file is empty. Please choose a non-empty JPEG, PNG, or WEBP image.",
            [_field_error("image", "EMPTY_IMAGE", "The image file is empty.")],
        )

    return image_bytes


def _failed_verification_result(
    application: ApplicationData,
    reason_code: str,
    latency_ms: int,
) -> VerificationResult:
    return VerificationResult(
        results=[
            FieldResult(
                field=field_name,
                match_type=FIELD_MATCH_TYPES[field_name],
                expected=getattr(application, field_name),
                found=None,
                status="FAIL",
                reason_code=reason_code,
            )
            for field_name in APPLICATION_FIELD_ORDER
        ],
        overall_verdict="NEEDS_REVIEW",
        latency_ms=latency_ms,
    )


def _finalize_verification_response(response: Response, result: VerificationResult) -> None:
    response.headers["X-Verification-Latency-ms"] = str(result.latency_ms)
    _log_verification_result(result)


def _log_verification_result(result: VerificationResult) -> None:
    failed_fields = [
        field_result.field for field_result in result.results if field_result.status == "FAIL"
    ]
    sla_exceeded = result.latency_ms >= SINGLE_LABEL_SLA_MS
    level = logging.WARNING if sla_exceeded else logging.INFO
    logger.log(
        level,
        "Verification completed.",
        extra={
            "latency_ms": result.latency_ms,
            "overall_verdict": result.overall_verdict,
            "sla_exceeded": sla_exceeded,
            "failed_fields": failed_fields,
        },
    )


def _log_batch_result(result: BatchVerificationResult, worker_count: int) -> None:
    item_sla_exceeded = any(
        item.result is not None and item.result.latency_ms >= SINGLE_LABEL_SLA_MS
        for item in result.items
    )
    level = logging.WARNING if item_sla_exceeded else logging.INFO
    logger.log(
        level,
        "Batch verification completed.",
        extra={
            "latency_ms": result.latency_ms,
            "item_count": result.summary.total,
            "passed": result.summary.passed,
            "needs_review": result.summary.needs_review,
            "worker_concurrency": worker_count,
            "item_sla_exceeded": item_sla_exceeded,
        },
    )


def _elapsed_ms(started_at: float) -> int:
    return max(0, round((perf_counter() - started_at) * 1000))


def _request_validation_fields(exc: RequestValidationError) -> list[dict[str, str]]:
    return [_validation_field(error) for error in exc.errors()]


def _pydantic_validation_fields(exc: ValidationError) -> list[dict[str, str]]:
    return [_validation_field(error) for error in exc.errors()]


def _validation_field(error: Any) -> dict[str, str]:
    field_name = _field_name_from_loc(error.get("loc", ()))
    error_type = str(error.get("type", "validation_error")).upper().replace(".", "_")

    if error_type == "MISSING":
        if field_name == "image":
            message = "Please upload a label image."
        else:
            message = f"Please provide {field_name.replace('_', ' ')}."
    else:
        message = str(error.get("msg", "Please check this field."))

    return _field_error(field_name, error_type, message)


def _field_name_from_loc(loc: Any) -> str:
    if not isinstance(loc, (list, tuple)):
        return "request"

    for value in reversed(loc):
        if isinstance(value, str) and value != "body":
            return value

    return "request"


def _field_error(field: str, code: str, message: str) -> dict[str, str]:
    return {"field": field, "code": code, "message": message}


def _error_response(
    status_code: int,
    code: str,
    message: str,
    fields: list[dict[str, str]] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {"code": code, "message": message}
    if fields:
        error["fields"] = fields

    return JSONResponse(status_code=status_code, content={"error": error})


def _format_bytes(size: int) -> str:
    if size >= 1024 * 1024 and size % (1024 * 1024) == 0:
        return f"{size // (1024 * 1024)} MB"
    if size >= 1024 and size % 1024 == 0:
        return f"{size // 1024} KB"
    return f"{size} bytes"

