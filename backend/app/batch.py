"""Bounded-concurrency orchestration for batch label verification."""

import asyncio
import logging
from time import perf_counter
from typing import Any

from fastapi import UploadFile

from backend.app.config import Settings
from backend.app.exceptions import ApiError, VisionProviderError
from backend.app.schemas import BatchItemResult, BatchSummary, BatchVerificationResult, ErrorField, ItemError
from backend.app.validation import APPLICATION_FIELD_ORDER, application_data_from_fields
from backend.app.verification import SINGLE_LABEL_SLA_MS, elapsed_ms, verify_single_upload
from backend.app.vision_service import VisionService

logger = logging.getLogger(__name__)


async def verify_batch(
    batch_items: list[dict[str, Any]],
    images: list[UploadFile],
    vision_service: VisionService,
    settings: Settings,
    started_at: float,
) -> BatchVerificationResult:
    """Verify batch items concurrently while isolating errors to their item."""
    semaphore = asyncio.Semaphore(settings.batch_worker_concurrency)

    async def verify_item(index: int, raw_item: dict[str, Any]) -> BatchItemResult:
        async with semaphore:
            return await verify_batch_item(index, raw_item, images[index], vision_service, settings)

    item_results = await asyncio.gather(
        *(verify_item(index, raw_item) for index, raw_item in enumerate(batch_items))
    )
    result = BatchVerificationResult(
        items=item_results,
        summary=batch_summary(item_results),
        latency_ms=elapsed_ms(started_at),
    )
    log_batch_result(result, settings.batch_worker_concurrency)
    return result


async def verify_batch_item(
    index: int,
    raw_item: dict[str, Any],
    image: UploadFile,
    vision_service: VisionService,
    settings: Settings,
) -> BatchItemResult:
    """Verify one batch item and return an item-level error instead of raising it."""
    client_id = batch_item_client_id(raw_item, index)
    filename = image.filename or None
    started_at = perf_counter()
    if not isinstance(raw_item, dict):
        return batch_item_error_result(
            index,
            client_id,
            filename,
            ApiError(
                422,
                "VALIDATION_ERROR",
                "Please provide label details for this item.",
                [
                    {
                        "field": "item",
                        "code": "INVALID_ITEM",
                        "message": "This batch item must be a set of label details.",
                    }
                ],
            ),
        )
    try:
        application = application_data_from_fields(
            **{field_name: raw_item.get(field_name, "") for field_name in APPLICATION_FIELD_ORDER}
        )
        result = await verify_single_upload(application, image, vision_service, settings, started_at)
        return BatchItemResult(
            client_id=client_id,
            index=index,
            filename=filename,
            status="COMPLETED",
            result=result,
            error=None,
        )
    except ApiError as exc:
        return batch_item_error_result(index, client_id, filename, exc)
    except VisionProviderError:
        logger.error(
            "Vision provider unavailable for batch item.",
            extra={"error_code": "VISION_PROVIDER_ERROR", "batch_item_index": index},
        )
        return batch_item_error_result(
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
        return batch_item_error_result(
            index,
            client_id,
            filename,
            ApiError(
                500,
                "INTERNAL_SERVER_ERROR",
                "Something went wrong while checking this label. Please try again.",
            ),
        )


def batch_item_client_id(raw_item: Any, index: int) -> str:
    """Return the submitted client identifier or a stable fallback identifier."""
    if isinstance(raw_item, dict):
        client_id = raw_item.get("client_id")
        if isinstance(client_id, str) and client_id.strip():
            return client_id.strip()
    return f"item-{index + 1}"


def batch_item_error_result(
    index: int,
    client_id: str,
    filename: str | None,
    error: ApiError,
) -> BatchItemResult:
    """Convert an expected item error to the public batch-item error contract."""
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


def batch_summary(item_results: list[BatchItemResult]) -> BatchSummary:
    """Count approved results and treat every other item as needing review."""
    passed = sum(
        1
        for item in item_results
        if item.result is not None and item.result.overall_verdict == "APPROVED"
    )
    total = len(item_results)
    return BatchSummary(passed=passed, needs_review=total - passed, total=total)


def log_batch_result(result: BatchVerificationResult, worker_count: int) -> None:
    """Log batch completion with latency and aggregate review counts."""
    item_sla_exceeded = any(
        item.result is not None and item.result.latency_ms >= SINGLE_LABEL_SLA_MS
        for item in result.items
    )
    logger.log(
        logging.WARNING if item_sla_exceeded else logging.INFO,
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
