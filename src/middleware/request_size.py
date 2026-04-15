from __future__ import annotations

from fastapi import HTTPException, status
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.config import Settings, get_settings


class RequestSizeMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        settings: Settings | None = None,
        max_body_bytes: int | None = None,
    ) -> None:
        self.app = app
        settings = settings or get_settings()
        self.max_body_bytes = max_body_bytes
        if self.max_body_bytes is None:
            self.max_body_bytes = settings.max_request_body_bytes

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        content_length = headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_body_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            f"Request body exceeds the configured limit of "
                            f"{self.max_body_bytes} bytes."
                        ),
                    )
            except ValueError:
                pass

        body_bytes_read = 0

        async def limited_receive() -> Message:
            nonlocal body_bytes_read
            message = await receive()
            if message["type"] == "http.request":
                body_bytes_read += len(message.get("body", b""))
                if body_bytes_read > self.max_body_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            f"Request body exceeds the configured limit of "
                            f"{self.max_body_bytes} bytes."
                        ),
                    )
            return message

        await self.app(scope, limited_receive, send)
