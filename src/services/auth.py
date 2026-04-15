from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from src.config import Settings, get_settings
from src.models.auth import AuthTokenClaims, AuthenticatedUser

AUTH_TOKEN_VERSION = 1
AUTH_TOKEN_TYPE_ACCESS = "access"


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _datetime_to_timestamp(value: datetime) -> int:
    return int(value.astimezone(UTC).timestamp())


def _timestamp_to_datetime(value: int) -> datetime:
    return datetime.fromtimestamp(value, tz=UTC)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class AuthService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _require_secret(self) -> bytes:
        secret = self.settings.auth_secret_key.strip()
        if not secret:
            raise ValueError("AUTH_SECRET_KEY is not configured.")
        return secret.encode("utf-8")

    def _build_payload(
        self,
        user: AuthenticatedUser,
        *,
        issued_at: datetime,
        expires_at: datetime,
        token_id: str,
    ) -> dict[str, object]:
        return {
            "ver": AUTH_TOKEN_VERSION,
            "typ": AUTH_TOKEN_TYPE_ACCESS,
            "iss": self.settings.auth_issuer,
            "aud": self.settings.auth_audience,
            "sub": user.user_id,
            "firm_id": user.firm_id,
            "email": user.email,
            "display_name": user.display_name,
            "global_role": user.global_role,
            "iat": _datetime_to_timestamp(issued_at),
            "exp": _datetime_to_timestamp(expires_at),
            "jti": token_id,
        }

    def issue_access_token(
        self,
        user: AuthenticatedUser,
        *,
        issued_at: datetime | None = None,
        expires_in: timedelta | None = None,
        token_id: str | None = None,
    ) -> str:
        secret = self._require_secret()
        now = _normalize_datetime(issued_at or datetime.now(UTC))
        ttl = expires_in or timedelta(
            minutes=self.settings.auth_access_token_ttl_minutes,
        )
        expires_at = now + ttl
        payload = self._build_payload(
            user,
            issued_at=now,
            expires_at=expires_at,
            token_id=token_id or secrets.token_urlsafe(16),
        )
        payload_bytes = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        payload_b64 = _base64url_encode(payload_bytes)
        signature = hmac.new(
            secret,
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return f"{payload_b64}.{_base64url_encode(signature)}"

    def verify_access_token(self, token: str) -> AuthTokenClaims:
        secret = self._require_secret()
        try:
            payload_b64, signature_b64 = token.split(".", maxsplit=1)
        except ValueError as exc:
            raise ValueError("Malformed access token.") from exc

        expected_signature = hmac.new(
            secret,
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).digest()
        signature = _base64url_decode(signature_b64)
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid access token signature.")

        payload = json.loads(_base64url_decode(payload_b64))
        if not isinstance(payload, dict):
            raise ValueError("Invalid access token payload.")

        version = payload.get("ver")
        token_type = payload.get("typ")
        issuer = payload.get("iss")
        audience = payload.get("aud")
        subject_id = payload.get("sub")
        firm_id = payload.get("firm_id")
        email = payload.get("email")
        display_name = payload.get("display_name")
        global_role = payload.get("global_role")
        issued_at = payload.get("iat")
        expires_at = payload.get("exp")
        token_id = payload.get("jti")

        if version != AUTH_TOKEN_VERSION:
            raise ValueError("Unsupported access token version.")
        if token_type != AUTH_TOKEN_TYPE_ACCESS:
            raise ValueError("Unsupported token type.")
        if issuer != self.settings.auth_issuer:
            raise ValueError("Invalid token issuer.")
        if audience != self.settings.auth_audience:
            raise ValueError("Invalid token audience.")

        required_fields = {
            "sub": subject_id,
            "firm_id": firm_id,
            "email": email,
            "display_name": display_name,
            "global_role": global_role,
            "iat": issued_at,
            "exp": expires_at,
            "jti": token_id,
        }
        missing_fields = [
            field_name
            for field_name, value in required_fields.items()
            if value in (None, "")
        ]
        if missing_fields:
            raise ValueError(
                "Access token payload is missing required fields: "
                + ", ".join(missing_fields),
            )

        if not isinstance(issued_at, int) or not isinstance(expires_at, int):
            raise ValueError("Access token timestamps must be integers.")

        now = datetime.now(UTC)
        skew = timedelta(seconds=self.settings.auth_clock_skew_seconds)
        issued_at_dt = _timestamp_to_datetime(issued_at)
        expires_at_dt = _timestamp_to_datetime(expires_at)

        if now + skew < issued_at_dt:
            raise ValueError("Access token is not valid yet.")
        if now - skew >= expires_at_dt:
            raise ValueError("Access token has expired.")

        return AuthTokenClaims(
            version=version,
            token_type=token_type,
            issuer=issuer,
            audience=audience,
            subject_id=subject_id,
            firm_id=firm_id,
            email=email,
            display_name=display_name,
            global_role=global_role,
            issued_at=issued_at_dt,
            expires_at=expires_at_dt,
            token_id=token_id,
        )
