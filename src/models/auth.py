from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    user_id: str
    firm_id: str
    email: str
    display_name: str
    global_role: str
    is_active: bool
    firm_status: str


@dataclass(frozen=True, slots=True)
class AuthTokenClaims:
    version: int
    token_type: str
    issuer: str
    audience: str
    subject_id: str
    firm_id: str
    email: str
    display_name: str
    global_role: str
    issued_at: datetime
    expires_at: datetime
    token_id: str


@dataclass(frozen=True, slots=True)
class AuthContext:
    authenticated: bool
    user: AuthenticatedUser | None = None
    claims: AuthTokenClaims | None = None
    token: str | None = None

    @classmethod
    def anonymous(cls) -> AuthContext:
        return cls(authenticated=False)

