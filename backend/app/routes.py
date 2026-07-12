"""Thin HTTP routes for health, single-label, and batch verification."""

from time import perf_counter
from typing import cast

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile

from backend.app.batch import verify_batch
from backend.app.config import Settings
from backend.app.schemas import BatchVerificationResult, VerificationResult
from backend.app.validation import (
    application_data_from_fields,
    batch_items_from_json,
    validate_batch_image_count,
    validate_batch_size,
)
from backend.app.verification import finalize_verification_response, verify_single_upload
from backend.app.vision_service import VisionService, get_vision_service

router = APIRouter()


def get_vision_service_dependency(request: Request) -> VisionService:
    """Build the configured vision service for one verification request."""
    return get_vision_service(cast(Settings, request.app.state.settings))


@router.get("/health")
def health() -> dict[str, str]:
    """Return the lightweight health-check response used by deployment platforms."""
    return {"status": "ok", "service": "ttb-label-verification-api"}


@router.post("/verify", response_model=VerificationResult)
async def verify_label(
    request: Request,
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
    """Verify one uploaded label against the submitted application fields."""
    started_at = perf_counter()
    application = application_data_from_fields(
        brand_name=brand_name,
        class_type=class_type,
        abv=abv,
        net_contents=net_contents,
        producer=producer,
        country_of_origin=country_of_origin,
        government_warning=government_warning,
    )
    result = await verify_single_upload(
        application,
        image,
        vision_service,
        cast(Settings, request.app.state.settings),
        started_at,
    )
    response.headers["X-Verification-Latency-ms"] = str(result.latency_ms)
    finalize_verification_response(result)
    return result


@router.post("/verify/batch", response_model=BatchVerificationResult)
async def verify_label_batch(
    request: Request,
    response: Response,
    items_json: str = Form(...),
    images: list[UploadFile] = File(...),
    vision_service: VisionService = Depends(get_vision_service_dependency),
) -> BatchVerificationResult:
    """Verify a bounded batch while returning an independent result for each item."""
    started_at = perf_counter()
    settings = cast(Settings, request.app.state.settings)
    batch_items = batch_items_from_json(items_json)
    validate_batch_size(batch_items, settings)
    validate_batch_image_count(batch_items, images)
    result = await verify_batch(batch_items, images, vision_service, settings, started_at)
    response.headers["X-Batch-Verification-Latency-ms"] = str(result.latency_ms)
    return result
