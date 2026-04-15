from __future__ import annotations

from collections.abc import Callable

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from src.errors import VALIDATION_ERROR
from src.middleware.auth import _error_response
from src.utils import get_request_id


class ValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        try:
            return await call_next(request)
        except RequestValidationError as error:
            return _error_response(
                code=VALIDATION_ERROR.code,
                message=VALIDATION_ERROR.message,
                status_code=VALIDATION_ERROR.status_code,
                request_id=get_request_id(),
                details={"errors": error.errors()},
            )
        except ValidationError as error:
            return _error_response(
                code=VALIDATION_ERROR.code,
                message=VALIDATION_ERROR.message,
                status_code=VALIDATION_ERROR.status_code,
                request_id=get_request_id(),
                details={"errors": error.errors()},
            )

