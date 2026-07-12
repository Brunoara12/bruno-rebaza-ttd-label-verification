"""Request payload and upload validation helpers for the verification API."""

import json
from json import JSONDecodeError
from typing import Any

from fastapi import UploadFile
from pydantic import ValidationError

from backend.app.config import Settings
from backend.app.exceptions import ApiError
from backend.app.schemas import ApplicationData

ACCEPTED_IMAGE_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
APPLICATION_FIELD_ORDER = (
    "brand_name",
    "class_type",
    "abv",
    "net_contents",
    "producer",
    "country_of_origin",
    "government_warning",
)


def application_data_from_fields(**raw_fields: str) -> ApplicationData:
    """Validate and normalize form-like application fields into ApplicationData."""
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
                field_error(
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
            pydantic_validation_fields(exc),
        ) from exc


def batch_items_from_json(items_json: str) -> list[dict[str, Any]]:
    """Decode the batch metadata JSON submitted alongside uploaded images."""
    try:
        batch_items = json.loads(items_json)
    except JSONDecodeError as exc:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "Please provide readable batch label details.",
            [field_error("items_json", "INVALID_JSON", "The batch details could not be read.")],
        ) from exc

    if not isinstance(batch_items, list):
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "Please provide one set of label details for each image.",
            [field_error("items_json", "INVALID_BATCH", "Batch details must be a list.")],
        )
    return batch_items


def validate_batch_size(batch_items: list[dict[str, Any]], settings: Settings) -> None:
    """Ensure a batch is nonempty and does not exceed the configured item limit."""
    if not batch_items:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "Please add at least one label to the batch.",
            [field_error("items_json", "EMPTY_BATCH", "The batch must include at least one label.")],
        )
    if len(batch_items) > settings.batch_max_items:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            f"Please check no more than {settings.batch_max_items} labels at once.",
            [
                field_error(
                    "items_json",
                    "TOO_MANY_ITEMS",
                    f"The batch has more than {settings.batch_max_items} labels.",
                )
            ],
        )


def validate_batch_image_count(batch_items: list[dict[str, Any]], images: list[UploadFile]) -> None:
    """Ensure each batch metadata entry has exactly one uploaded image."""
    if len(images) != len(batch_items):
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "Please provide one image for each label in the batch.",
            [
                field_error(
                    "images",
                    "BATCH_IMAGE_COUNT_MISMATCH",
                    "The number of images must match the number of label detail rows.",
                )
            ],
        )


def validate_upload_content_type(upload_file: UploadFile) -> None:
    """Reject uploads outside the image MIME types accepted by the API."""
    if upload_file.content_type not in ACCEPTED_IMAGE_MIME_TYPES:
        raise ApiError(
            422,
            "UNSUPPORTED_FILE_TYPE",
            "Please upload a JPEG, PNG, or WEBP image.",
            [
                field_error(
                    "image",
                    "UNSUPPORTED_FILE_TYPE",
                    "Accepted image types are JPEG, PNG, and WEBP.",
                )
            ],
        )


async def read_upload_bytes(upload_file: UploadFile, settings: Settings) -> bytes:
    """Read a nonempty upload while enforcing the configured byte limit."""
    upload_limit = settings.max_upload_bytes
    image_bytes = await upload_file.read(upload_limit + 1)
    if len(image_bytes) > upload_limit:
        raise ApiError(
            413,
            "FILE_TOO_LARGE",
            f"Please upload an image smaller than {format_bytes(upload_limit)}.",
            [
                field_error(
                    "image",
                    "FILE_TOO_LARGE",
                    f"The image is larger than {format_bytes(upload_limit)}.",
                )
            ],
        )
    if not image_bytes:
        raise ApiError(
            400,
            "EMPTY_IMAGE",
            "The image file is empty. Please choose a non-empty JPEG, PNG, or WEBP image.",
            [field_error("image", "EMPTY_IMAGE", "The image file is empty.")],
        )
    return image_bytes


def request_validation_fields(exc: ValidationError) -> list[dict[str, str]]:
    """Convert FastAPI or Pydantic validation details to the public field format."""
    return [validation_field(error) for error in exc.errors()]


def pydantic_validation_fields(exc: ValidationError) -> list[dict[str, str]]:
    """Convert Pydantic model validation details to the public field format."""
    return [validation_field(error) for error in exc.errors()]


def field_error(field: str, code: str, message: str) -> dict[str, str]:
    """Create one client-safe field error payload."""
    return {"field": field, "code": code, "message": message}


def validation_field(error: Any) -> dict[str, str]:
    """Translate one framework validation error into the stable API shape."""
    field_name = field_name_from_loc(error.get("loc", ()))
    error_type = str(error.get("type", "validation_error")).upper().replace(".", "_")
    if error_type == "MISSING":
        message = "Please upload a label image." if field_name == "image" else (
            f"Please provide {field_name.replace('_', ' ')}."
        )
    else:
        message = str(error.get("msg", "Please check this field."))
    return field_error(field_name, error_type, message)


def field_name_from_loc(loc: Any) -> str:
    """Find the user-facing field name from a framework validation location."""
    if not isinstance(loc, (list, tuple)):
        return "request"
    for value in reversed(loc):
        if isinstance(value, str) and value != "body":
            return value
    return "request"


def format_bytes(size: int) -> str:
    """Format a byte count for a concise validation message."""
    if size >= 1024 * 1024 and size % (1024 * 1024) == 0:
        return f"{size // (1024 * 1024)} MB"
    if size >= 1024 and size % 1024 == 0:
        return f"{size // 1024} KB"
    return f"{size} bytes"
