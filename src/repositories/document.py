from datetime import datetime

from sqlalchemy import func, select

from src.models.document import Document
from src.schemas.enum import DocumentStatus

from .base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    model = Document

    def find_by_workspace_and_checksum(
        self,
        workspace_id: str,
        checksum: str,
    ) -> Document | None:
        statement = select(self.model).where(
            self.model.workspace_id == workspace_id,
            self.model.checksum == checksum,
        )
        return self.session.scalar(statement)

    def count_by_workspace(self, workspace_id: str) -> int:
        statement = select(func.count()).select_from(self.model).where(
            self.model.workspace_id == workspace_id,
        )
        return int(self.session.scalar(statement) or 0)

    def list_by_workspace(
        self,
        workspace_id: str,
        *,
        document_type: str | None = None,
        status: DocumentStatus | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:
        statement = select(self.model).where(self.model.workspace_id == workspace_id)
        if document_type is not None:
            statement = statement.where(self.model.document_type == document_type)
        if status is not None:
            statement = statement.where(self.model.status == status)
        if created_after is not None:
            statement = statement.where(self.model.created_at >= created_after)
        if created_before is not None:
            statement = statement.where(self.model.created_at <= created_before)

        statement = statement.order_by(self.model.created_at.desc(), self.model.id.desc())
        statement = statement.limit(limit).offset(offset)
        return list(self.session.scalars(statement).all())
