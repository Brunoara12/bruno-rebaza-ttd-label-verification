"""Single-label verification orchestration, timing, and result logging."""

import asyncio
import logging
from time import perf_counter

from fastapi import UploadFile

from backend.app.comparison import compare_label
from backend.app.config import Settings
from backend.app.exceptions import ApiError, VisionParseError, VisionTimeoutError
from backend.app.image_preprocess import ImagePreprocessError, preprocess_image
from backend.app.schemas import ApplicationData, FieldResult, VerificationResult
from backend.app.validation import APPLICATION_FIELD_ORDER, field_error, read_upload_bytes, validate_upload_content_type
from backend.app.vision_service import VisionService

logger = logging.getLogger(__name__)

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
SINGLE_LABEL_RESPONSE_BUFFER_SECONDS = 0.2


async def verify_single_upload(
    application: ApplicationData,
    image: UploadFile,
    vision_service: VisionService,
    settings: Settings,
    started_at: float,
) -> VerificationResult:
    """Validate, preprocess, extract, and compare one uploaded label image."""
    validate_upload_content_type(image)
    image_bytes = await read_upload_bytes(image, settings)
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
                field_error(
                    "image",
                    "INVALID_IMAGE",
                    "The image file is corrupt or unsupported.",
                )
            ],
        ) from exc

    try:
        extracted_label = await asyncio.wait_for(
            asyncio.to_thread(vision_service.extract_label, preprocessed_image),
            timeout=remaining_model_timeout_seconds(started_at, settings),
        )
    except (VisionTimeoutError, asyncio.TimeoutError):
        return failed_verification_result(application, "MODEL_TIMEOUT", elapsed_ms(started_at))
    except VisionParseError:
        return failed_verification_result(application, "PARSE_ERROR", elapsed_ms(started_at))

    result = compare_label(application, extracted_label)
    return result.model_copy(update={"latency_ms": elapsed_ms(started_at)})


def failed_verification_result(
    application: ApplicationData,
    reason_code: str,
    latency_ms: int,
) -> VerificationResult:
    """Build a reviewable result for a timed-out or unparsable model response."""
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


def finalize_verification_response(result: VerificationResult) -> None:
    """Log one completed single-label result after its response is finalized."""
    failed_fields = [field_result.field for field_result in result.results if field_result.status == "FAIL"]
    sla_exceeded = result.latency_ms >= SINGLE_LABEL_SLA_MS
    logger.log(
        logging.WARNING if sla_exceeded else logging.INFO,
        "Verification completed.",
        extra={
            "latency_ms": result.latency_ms,
            "overall_verdict": result.overall_verdict,
            "sla_exceeded": sla_exceeded,
            "failed_fields": failed_fields,
        },
    )


def elapsed_ms(started_at: float) -> int:
    """Return nonnegative elapsed milliseconds from an endpoint start time."""
    return max(0, round((perf_counter() - started_at) * 1000))


def remaining_model_timeout_seconds(started_at: float, settings: Settings) -> float:
    """Limit model work to the configured budget and the five-second response SLA."""
    elapsed_seconds = max(0.0, perf_counter() - started_at)
    remaining_sla_seconds = (SINGLE_LABEL_SLA_MS / 1000) - elapsed_seconds
    guarded_timeout = remaining_sla_seconds - SINGLE_LABEL_RESPONSE_BUFFER_SECONDS
    return max(0.05, min(settings.vision_timeout_seconds, guarded_timeout))
