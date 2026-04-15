from sqlalchemy import desc, select

from src.models.audit_event import AuditEvent

from .base import BaseRepository


class AuditEventRepository(BaseRepository[AuditEvent]):
    model = AuditEvent

    def list_by_workspace(
        self,
        workspace_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditEvent]:
        statement = (
            select(self.model)
            .where(self.model.workspace_id == workspace_id)
            .order_by(desc(self.model.created_at), desc(self.model.id))
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement).all())
