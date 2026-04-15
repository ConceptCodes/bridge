from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import status


@dataclass(frozen=True, slots=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int = status.HTTP_400_BAD_REQUEST
    details: dict[str, Any] | None = field(default=None)

    def with_details(self, **details: Any) -> AppError:
        return AppError(
            code=self.code,
            message=self.message,
            status_code=self.status_code,
            details=details or None,
        )

    def __str__(self) -> str:
        return self.message


BAD_REQUEST = AppError(
    code="bad_request",
    message="The request could not be processed.",
    status_code=status.HTTP_400_BAD_REQUEST,
)
VALIDATION_ERROR = AppError(
    code="validation_error",
    message="Request validation failed.",
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
)
UNAUTHORIZED = AppError(
    code="unauthorized",
    message="Authentication is required.",
    status_code=status.HTTP_401_UNAUTHORIZED,
)
FORBIDDEN = AppError(
    code="forbidden",
    message="You do not have permission to perform this action.",
    status_code=status.HTTP_403_FORBIDDEN,
)
NOT_FOUND = AppError(
    code="not_found",
    message="The requested resource was not found.",
    status_code=status.HTTP_404_NOT_FOUND,
)
CONFLICT = AppError(
    code="conflict",
    message="The request conflicts with the current state.",
    status_code=status.HTTP_409_CONFLICT,
)
UNSUPPORTED_MEDIA_TYPE = AppError(
    code="unsupported_media_type",
    message="Unsupported Content-Type header.",
    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
)
REQUEST_ENTITY_TOO_LARGE = AppError(
    code="request_entity_too_large",
    message="Request body is too large.",
    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
)
INTERNAL_SERVER_ERROR = AppError(
    code="internal_server_error",
    message="An unexpected error occurred.",
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
)


DEFAULT_ERRORS: dict[str, AppError] = {
    error.code: error
    for error in (
        BAD_REQUEST,
        VALIDATION_ERROR,
        UNAUTHORIZED,
        FORBIDDEN,
        NOT_FOUND,
        CONFLICT,
        UNSUPPORTED_MEDIA_TYPE,
        REQUEST_ENTITY_TOO_LARGE,
        INTERNAL_SERVER_ERROR,
    )
}

__all__ = [
    "AppError",
    "BAD_REQUEST",
    "CONFLICT",
    "DEFAULT_ERRORS",
    "FORBIDDEN",
    "INTERNAL_SERVER_ERROR",
    "NOT_FOUND",
    "REQUEST_ENTITY_TOO_LARGE",
    "UNAUTHORIZED",
    "UNSUPPORTED_MEDIA_TYPE",
    "VALIDATION_ERROR",
]
