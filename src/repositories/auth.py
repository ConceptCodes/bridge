from __future__ import annotations

from sqlalchemy import select

from src.models import AuthenticatedUser, Firm, User
from src.schemas.enum import FirmStatus

from .base import BaseRepository


class AuthRepository(BaseRepository[User]):
    model = User

    def load_authenticated_user(self, subject_id: str) -> AuthenticatedUser:
        statement = (
            select(User, Firm)
            .join(Firm, Firm.id == User.firm_id)
            .where(User.id == subject_id)
        )
        row = self.session.execute(statement).one_or_none()
        if row is None:
            raise ValueError("User does not exist.")

        user, firm = row
        if user.firm_id != firm.id:
            raise ValueError("User firm does not exist.")
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
