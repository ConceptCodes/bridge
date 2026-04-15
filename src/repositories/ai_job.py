from src.models.ai_job import AIJob

from .base import BaseRepository


class AIJobRepository(BaseRepository[AIJob]):
    model = AIJob
