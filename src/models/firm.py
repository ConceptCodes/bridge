from __future__ import annotations

from sqlalchemy import Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from src.schemas.enum import FirmStatus


class Firm(Base):
    __tablename__ = "firms"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[FirmStatus] = mapped_column(
        SAEnum(
            FirmStatus,
            name="firm_status",
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
    )
