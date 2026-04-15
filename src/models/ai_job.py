from __future__ import annotations

from datetime import datetime

from sqlalchemy import Enum as SAEnum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, relationship, mapped_column

from src.schemas.enum import AIJobStatus

from .base import Base


class AIJob(Base):
    __tablename__ = "ai_jobs"
    __table_args__ = (
        Index("ix_ai_jobs_request_status", "research_request_id", "status"),
    )

    research_request_id: Mapped[str] = mapped_column(
        ForeignKey("research_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[AIJobStatus] = mapped_column(
        SAEnum(
            AIJobStatus,
            name="ai_job_status",
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
    )
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)
    queued_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    research_request: Mapped["ResearchRequest"] = relationship(
        "ResearchRequest",
        back_populates="jobs",
    )
