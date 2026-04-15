from __future__ import annotations

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.logger.main import get_logger
from src.middleware.request_id import get_request_id

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        start = time.perf_counter()
        response_status = 500

        try:
            response = await call_next(request)
            response_status = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            request_id = get_request_id()
            logger.info(
                "http_request method=%s path=%s status=%s "
                "duration_ms=%.2f request_id=%s",
                request.method,
                request.url.path,
                response_status,
                duration_ms,
                request_id,
            )
