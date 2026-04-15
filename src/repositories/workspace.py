from sqlalchemy import desc, select

from src.models.workspace import Workspace
from src.schemas.enum import WorkspaceStatus, WorkflowType

from .base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    model = Workspace

    def list_filtered(
        self,
        *,
        firm_id: str | None = None,
        status: WorkspaceStatus | None = None,
        workflow_type: WorkflowType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Workspace]:
        statement = select(self.model)
        if firm_id is not None:
            statement = statement.where(self.model.firm_id == firm_id)
        if status is not None:
            statement = statement.where(self.model.status == status)
        if workflow_type is not None:
            statement = statement.where(self.model.workflow_type == workflow_type)

        statement = statement.order_by(desc(self.model.created_at), desc(self.model.id))
        statement = statement.limit(limit).offset(offset)
        return list(self.session.scalars(statement).all())
