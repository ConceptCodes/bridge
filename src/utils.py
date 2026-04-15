from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

from src.models.auth import AuthContext, AuthenticatedUser

request_id_context: ContextVar[str | None] = ContextVar(
    "request_id_context",
    default=None,
)

auth_context_var: ContextVar[AuthContext | None] = ContextVar(
    "auth_context",
    default=None,
)


def get_request_id() -> str | None:
    return request_id_context.get()


def get_auth_context() -> AuthContext | None:
    return auth_context_var.get()


def get_current_user() -> AuthenticatedUser | None:
    context = get_auth_context()
    if context is None:
        return None
    return context.user


def create_request_id() -> str:
    return uuid4().hex

