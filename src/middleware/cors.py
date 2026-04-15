from __future__ import annotations

from collections.abc import Sequence

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class CorsMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        allow_origins: Sequence[str] | None = None,
        allow_methods: Sequence[str] | None = None,
        allow_headers: Sequence[str] | None = None,
        allow_credentials: bool = False,
        max_age: int = 600,
    ) -> None:
        super().__init__(app)
        self.allow_origins = tuple(allow_origins or ("*",))
        self.allow_methods = tuple(
            allow_methods or ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
        )
        self.allow_headers = tuple(allow_headers or ("*",))
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    def _get_allow_origin(self, origin: str | None) -> str:
        if "*" in self.allow_origins:
            return "*"
        if origin in self.allow_origins:
            return origin
        return ""

    def _add_cors_headers(self, response: Response, origin: str | None) -> Response:
        allow_origin = self._get_allow_origin(origin)
        if not allow_origin:
            return response

        response.headers["Access-Control-Allow-Origin"] = allow_origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        response.headers["Access-Control-Max-Age"] = str(self.max_age)
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        origin = request.headers.get("origin")

        if request.method == "OPTIONS" and origin:
            response = Response(status_code=204)
            return self._add_cors_headers(response, origin)

        response = await call_next(request)
        return self._add_cors_headers(response, origin)
