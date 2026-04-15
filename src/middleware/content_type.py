from __future__ import annotations

from collections.abc import Callable, Sequence

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import Settings, get_settings
from src.errors import UNSUPPORTED_MEDIA_TYPE


def _matches_content_type(content_type: str, allowed_type: str) -> bool:
    content_type = content_type.split(";", maxsplit=1)[0].strip().lower()
    if allowed_type.endswith("/*+json"):
        return content_type.endswith("+json")
    return content_type == allowed_type


class ContentTypeMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        settings: Settings | None = None,
        allowed_content_types: Sequence[str] | None = None,
        body_methods: Sequence[str] | None = None,
    ) -> None:
        super().__init__(app)
        settings = settings or get_settings()
        self.allowed_content_types = (
            tuple(content_type.lower() for content_type in allowed_content_types)
            if allowed_content_types is not None
            else settings.content_type_allowed_types
        )
        self.body_methods = (
            {method.upper() for method in body_methods}
            if body_methods is not None
            else set(settings.content_type_body_methods)
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        if request.method in self.body_methods:
            content_type = request.headers.get("content-type")
            if content_type is None:
                raise UNSUPPORTED_MEDIA_TYPE.with_details(
                    detail="Missing Content-Type header.",
                )

            normalized_content_type = content_type.lower()
            if not any(
                _matches_content_type(normalized_content_type, allowed_type)
                for allowed_type in self.allowed_content_types
            ):
                raise UNSUPPORTED_MEDIA_TYPE.with_details(
                    detail=f"Unsupported Content-Type: {content_type}",
                )

        response = await call_next(request)
        return response
