from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, relationship, mapped_column

from .base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("firm_id", "email", name="uq_users_firm_email"),
    )

    firm_id: Mapped[str] = mapped_column(
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    global_role: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    firm: Mapped["Firm"] = relationship("Firm", back_populates="users")
    created_workspaces: Mapped[list["Workspace"]] = relationship(
        "Workspace",
        back_populates="created_by_user",
    )
    workspace_memberships: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember",
        back_populates="user",
    )
    uploaded_documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="uploaded_by_user",
    )
    created_research_requests: Mapped[list["ResearchRequest"]] = relationship(
        "ResearchRequest",
        back_populates="created_by_user",
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        "AuditEvent",
        back_populates="actor_user",
    )
