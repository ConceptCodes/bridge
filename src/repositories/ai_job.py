from sqlalchemy import desc, select

from src.models.ai_job import AIJob
from src.models.research_request import ResearchRequest
from src.schemas.enum import AIJobStatus

from .base import BaseRepository


class AIJobRepository(BaseRepository[AIJob]):
    model = AIJob

    def find_by_research_request_and_active_status(
        self,
        research_request_id: str,
    ) -> AIJob | None:
        statement = select(self.model).where(
            self.model.research_request_id == research_request_id,
            self.model.status.in_(
                (
                    AIJobStatus.queued,
                    AIJobStatus.running,
                ),
            ),
        )
        return self.session.scalar(statement)

    def find_latest_for_workspace(self, workspace_id: str) -> AIJob | None:
        statement = (
            select(self.model)
            .join(ResearchRequest, ResearchRequest.id == self.model.research_request_id)
            .where(ResearchRequest.workspace_id == workspace_id)
            .order_by(desc(self.model.created_at), desc(self.model.id))
            .limit(1)
        )
        return self.session.scalar(statement)
