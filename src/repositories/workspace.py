from src.models.workspace import Workspace

from .base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    model = Workspace
