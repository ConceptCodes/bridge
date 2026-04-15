from src.models.research_request import ResearchRequest

from .base import BaseRepository


class ResearchRequestRepository(BaseRepository[ResearchRequest]):
    model = ResearchRequest
