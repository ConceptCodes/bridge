from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.errors import (
    BAD_REQUEST,
    CONFLICT,
    INTERNAL_SERVER_ERROR,
    REQUEST_ENTITY_TOO_LARGE,
    UNSUPPORTED_MEDIA_TYPE,
    VALIDATION_ERROR,
    AppError,
)
from src.utils import get_request_id


def _serialize_error(error: AppError) -> dict[str, object]:
    payload: dict[str, object] = {
        "code": error.code,
        "message": error.message,
    }
    if error.details is not None:
        payload["details"] = error.details
    return payload


def _error_response(error: AppError, request_id: str | None) -> JSONResponse:
    body: dict[str, object] = {
        "error": _serialize_error(error),
        "request_id": request_id,
    }
    response = JSONResponse(status_code=error.status_code, content=body)
    if request_id is not None:
        response.headers["X-Request-ID"] = request_id
    return response


class ErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        try:
            return await call_next(request)
        except AppError as error:
            return _error_response(error, get_request_id())
        except RequestValidationError as error:
            validation_error = VALIDATION_ERROR.with_details(
                errors=error.errors(),
            )
            return _error_response(validation_error, get_request_id())
        except HTTPException as error:
            if error.status_code == UNSUPPORTED_MEDIA_TYPE.status_code:
                app_error = UNSUPPORTED_MEDIA_TYPE.with_details(
                    detail=error.detail,
                )
            elif error.status_code == REQUEST_ENTITY_TOO_LARGE.status_code:
                app_error = REQUEST_ENTITY_TOO_LARGE.with_details(
                    detail=error.detail,
                )
            elif error.status_code == BAD_REQUEST.status_code:
                app_error = BAD_REQUEST.with_details(detail=error.detail)
            elif error.status_code == CONFLICT.status_code:
                app_error = CONFLICT.with_details(detail=error.detail)
            else:
                app_error = AppError(
                    code="http_error",
                    message=str(error.detail),
                    status_code=error.status_code,
                    details={"detail": error.detail} if error.detail else None,
                )
            return _error_response(app_error, get_request_id())
        except Exception:
            return _error_response(INTERNAL_SERVER_ERROR, get_request_id())
