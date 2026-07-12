"""Client-safe FastAPI exception handlers and response shaping."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.exceptions import ApiError, VisionProviderError
from backend.app.validation import request_validation_fields

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register the API's stable client-safe exception handlers."""

    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message, exc.fields)

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        _: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return error_response(
            422,
            "VALIDATION_ERROR",
            "Please provide an image and all required application fields.",
            request_validation_fields(exc),
        )

    @app.exception_handler(VisionProviderError)
    async def vision_provider_error_handler(_: Request, exc: VisionProviderError) -> JSONResponse:
        logger.error("Vision provider unavailable.", extra={"error_code": "VISION_PROVIDER_ERROR"})
        return error_response(
            502,
            "VISION_PROVIDER_ERROR",
            "The vision service is unavailable. Please try again later.",
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = "The requested endpoint was not found."
        if exc.status_code != 404 and exc.detail:
            message = str(exc.detail)
        return error_response(exc.status_code, "HTTP_ERROR", message)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, _: Exception) -> JSONResponse:
        logger.error(
            "Unhandled server error.",
            extra={"error_code": "UNHANDLED_SERVER_ERROR", "path": request.url.path},
        )
        return error_response(
            500,
            "INTERNAL_SERVER_ERROR",
            "Something went wrong while verifying the label. Please try again.",
        )


def error_response(
    status_code: int,
    code: str,
    message: str,
    fields: list[dict[str, str]] | None = None,
) -> JSONResponse:
    """Return the stable public error body used by all API error handlers."""
    error: dict[str, Any] = {"code": code, "message": message}
    if fields:
        error["fields"] = fields
    return JSONResponse(status_code=status_code, content={"error": error})
