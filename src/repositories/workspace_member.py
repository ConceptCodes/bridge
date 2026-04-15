from src.models.workspace_member import WorkspaceMember

from .base import BaseRepository


class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    model = WorkspaceMember
