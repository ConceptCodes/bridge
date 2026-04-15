from __future__ import annotations

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.schemas.enum import FirmStatus

from .base import Base


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
