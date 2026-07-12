"""Shared exceptions used across API, validation, and vision-service modules."""


class ApiError(Exception):
    """Represent a client-safe API error with an HTTP status and optional field details."""

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


class VisionServiceError(RuntimeError):
    """Base class for expected vision-service failures."""


class VisionTimeoutError(VisionServiceError):
    """Raised when the model call exceeds its configured timeout budget."""


class VisionParseError(VisionServiceError):
    """Raised when a model response cannot be validated as extraction data."""


class VisionProviderError(VisionServiceError):
    """Raised for provider configuration and non-timeout provider failures."""
