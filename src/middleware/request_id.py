from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

request_id_context: ContextVar[str | None] = ContextVar(
    "request_id_context",
    default=None,
)


def get_request_id() -> str | None:
    return request_id_context.get()


class RequestIdMiddleware(BaseHTTPMiddleware):
    header_name = "X-Request-ID"

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        request_id = request.headers.get(self.header_name) or uuid4().hex
        token = request_id_context.set(request_id)
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        finally:
            request_id_context.reset(token)

        response.headers[self.header_name] = request_id
        return response
