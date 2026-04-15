from __future__ import annotations

from collections.abc import Callable, Sequence

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.main import Settings, get_settings
from src.errors import FORBIDDEN, UNAUTHORIZED
from src.logger.main import get_logger
from src.models import AuthContext, AuthenticatedUser, Firm, User
from src.schemas.enum import FirmStatus
from src.services.auth import AuthService
from src.storage.sqlite.client import DatabaseClient, database_client
from src.utils import auth_context_var, get_request_id

logger = get_logger(__name__)


def _error_response(
    *,
    code: str,
    message: str,
    status_code: int,
    request_id: str | None,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    error: dict[str, object] = {
        "code": code,
        "message": message,
    }
    if details is not None:
        error["details"] = details

    body: dict[str, object] = {
        "error": error,
        "request_id": request_id,
    }
    response = JSONResponse(status_code=status_code, content=body)
    if request_id is not None:
        response.headers["X-Request-ID"] = request_id
    response.headers["WWW-Authenticate"] = "Bearer"
    return response


def _extract_bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ValueError("Authorization header must use the Bearer scheme.")
    return token.strip()


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        settings: Settings | None = None,
        auth_service: AuthService | None = None,
        database: DatabaseClient | None = None,
        public_path_prefixes: Sequence[str] | None = None,
        require_auth: bool | None = None,
    ) -> None:
        super().__init__(app)
        self.settings = settings or get_settings()
        self.auth_service = auth_service or AuthService(self.settings)
        self.database = database or database_client
        self.public_path_prefixes = tuple(
            public_path_prefixes
            if public_path_prefixes is not None
            else self.settings.auth_public_path_prefixes
        )
        self.require_auth = (
            require_auth if require_auth is not None else self.settings.auth_required
        )

    def _is_public_path(self, path: str) -> bool:
        return any(
            path == prefix or path.startswith(f"{prefix}/")
            for prefix in self.public_path_prefixes
        )

    def _load_user(self, subject_id: str) -> AuthenticatedUser:
        with self.database.session() as session:
            user = session.get(User, subject_id)
            if user is None:
                raise ValueError("User does not exist.")

            firm = session.get(Firm, user.firm_id)
            if firm is None:
                raise ValueError("Firm does not exist.")

            if not user.is_active:
                raise PermissionError("User account is disabled.")
            if firm.status != FirmStatus.active:
                raise PermissionError("Firm is not active.")

            return AuthenticatedUser(
                user_id=user.id,
                firm_id=user.firm_id,
                email=user.email,
                display_name=user.display_name,
                global_role=user.global_role,
                is_active=user.is_active,
                firm_status=firm.status.value,
            )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        request_id = get_request_id() or getattr(request.state, "request_id", None)
        path = request.url.path

        try:
            token = _extract_bearer_token(request.headers.get("authorization"))
        except ValueError as error:
            logger.debug("Rejecting request with malformed authorization header")
            return _error_response(
                code=UNAUTHORIZED.code,
                message=UNAUTHORIZED.message,
                status_code=UNAUTHORIZED.status_code,
                request_id=request_id,
                details={"detail": str(error)},
            )

        if token is None:
            context = AuthContext.anonymous()
            if self.require_auth and not self._is_public_path(path):
                return _error_response(
                    code=UNAUTHORIZED.code,
                    message=UNAUTHORIZED.message,
                    status_code=UNAUTHORIZED.status_code,
                    request_id=request_id,
                )

            request.state.auth = context
            request.state.user = None
            token_var = auth_context_var.set(context)
            try:
                response = await call_next(request)
            finally:
                auth_context_var.reset(token_var)
            return response

        try:
            claims = self.auth_service.verify_access_token(token)
            user = self._load_user(claims.subject_id)
            context = AuthContext(
                authenticated=True,
                user=user,
                claims=claims,
                token=token,
            )
        except ValueError as error:
            logger.debug("Rejecting request with invalid access token: %s", error)
            return _error_response(
                code=UNAUTHORIZED.code,
                message=UNAUTHORIZED.message,
                status_code=UNAUTHORIZED.status_code,
                request_id=request_id,
                details={"detail": str(error)},
            )
        except PermissionError as error:
            logger.debug("Rejecting request for inactive principal: %s", error)
            return _error_response(
                code=FORBIDDEN.code,
                message=FORBIDDEN.message,
                status_code=FORBIDDEN.status_code,
                request_id=request_id,
                details={"detail": str(error)},
            )

        request.state.auth = context
        request.state.user = context.user
        token_var = auth_context_var.set(context)
        try:
            response = await call_next(request)
        finally:
            auth_context_var.reset(token_var)
        return response
