from __future__ import annotations

from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.errors import UNSUPPORTED_MEDIA_TYPE

ALLOWED_CONTENT_TYPES = (
    "application/json",
    "application/*+json",
    "application/x-www-form-urlencoded",
    "multipart/form-data",
)
BODY_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _matches_content_type(content_type: str, allowed_type: str) -> bool:
    content_type = content_type.split(";", maxsplit=1)[0].strip().lower()
    if allowed_type.endswith("/*+json"):
        return content_type.endswith("+json")
    return content_type == allowed_type


class ContentTypeMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        if request.method in BODY_METHODS:
            content_type = request.headers.get("content-type")
            if content_type is None:
                raise UNSUPPORTED_MEDIA_TYPE.with_details(
                    detail="Missing Content-Type header.",
                )

            normalized_content_type = content_type.lower()
            if not any(
                _matches_content_type(normalized_content_type, allowed_type)
                for allowed_type in ALLOWED_CONTENT_TYPES
            ):
                raise UNSUPPORTED_MEDIA_TYPE.with_details(
                    detail=f"Unsupported Content-Type: {content_type}",
                )

        response = await call_next(request)
        return response
