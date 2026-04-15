from __future__ import annotations

from sqlalchemy import ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, relationship, mapped_column

from .base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_workspace_created_at", "workspace_id", "created_at"),
    )

    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="audit_events")
    actor_user: Mapped["User"] = relationship("User", back_populates="audit_events")
