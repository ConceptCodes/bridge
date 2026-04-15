from __future__ import annotations

from sqlalchemy import Enum as SAEnum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, relationship, mapped_column

from src.schemas.enum import ResearchRequestStatus

from .base import Base


class ResearchRequest(Base):
    __tablename__ = "research_requests"
    __table_args__ = (
        Index("ix_research_requests_workspace_created_at", "workspace_id", "created_at"),
    )

    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    question: Mapped[str] = mapped_column(String(4000), nullable=False)
    priority: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[ResearchRequestStatus] = mapped_column(
        SAEnum(
            ResearchRequestStatus,
            name="research_request_status",
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="research_requests")
    created_by_user: Mapped["User"] = relationship("User", back_populates="created_research_requests")
    jobs: Mapped[list["AIJob"]] = relationship("AIJob", back_populates="research_request")
