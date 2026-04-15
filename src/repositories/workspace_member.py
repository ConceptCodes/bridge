from sqlalchemy import func, select

from src.models.workspace_member import WorkspaceMember

from .base import BaseRepository


class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    model = WorkspaceMember

    def find_by_workspace_and_user(
        self,
        workspace_id: str,
        user_id: str,
    ) -> WorkspaceMember | None:
        statement = select(self.model).where(
            self.model.workspace_id == workspace_id,
            self.model.user_id == user_id,
        )
        return self.session.scalar(statement)

    def count_by_workspace(self, workspace_id: str) -> int:
        statement = select(func.count()).select_from(self.model).where(
            self.model.workspace_id == workspace_id,
        )
        return int(self.session.scalar(statement) or 0)
