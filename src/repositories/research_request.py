from sqlalchemy import func, select

from src.models.research_request import ResearchRequest
from src.schemas.enum import ResearchRequestStatus

from .base import BaseRepository


class ResearchRequestRepository(BaseRepository[ResearchRequest]):
    model = ResearchRequest

    def count_open_by_workspace(self, workspace_id: str) -> int:
        statement = select(func.count()).select_from(self.model).where(
            self.model.workspace_id == workspace_id,
            self.model.status.in_(
                (
                    ResearchRequestStatus.open,
                    ResearchRequestStatus.queued,
                    ResearchRequestStatus.in_progress,
                ),
            ),
        )
        return int(self.session.scalar(statement) or 0)
