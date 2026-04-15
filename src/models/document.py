from __future__ import annotations

from sqlalchemy import BigInteger, Enum as SAEnum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, relationship, mapped_column

from src.schemas.enum import DocumentStatus

from .base import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("workspace_id", "checksum", name="uq_documents_workspace_checksum"),
        Index("ix_documents_workspace_created_at", "workspace_id", "created_at"),
    )

    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(
            DocumentStatus,
            name="document_status",
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="documents")
    uploaded_by_user: Mapped["User"] = relationship("User", back_populates="uploaded_documents")
