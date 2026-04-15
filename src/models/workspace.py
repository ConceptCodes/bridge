from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, relationship, mapped_column

from src.schemas.enum import WorkspaceStatus, WorkflowType

from .base import Base


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        Index("ix_workspaces_firm_created_at", "firm_id", "created_at"),
    )

    firm_id: Mapped[str] = mapped_column(
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_external_ref: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    workflow_type: Mapped[WorkflowType] = mapped_column(
        SAEnum(
            WorkflowType,
            name="workflow_type",
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
    )
    tax_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[WorkspaceStatus] = mapped_column(
        SAEnum(
            WorkspaceStatus,
            name="workspace_status",
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    firm: Mapped["Firm"] = relationship("Firm", back_populates="workspaces")
    created_by_user: Mapped["User"] = relationship("User", back_populates="created_workspaces")
    members: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember",
        back_populates="workspace",
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="workspace",
    )
    research_requests: Mapped[list["ResearchRequest"]] = relationship(
        "ResearchRequest",
        back_populates="workspace",
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        "AuditEvent",
        back_populates="workspace",
    )
