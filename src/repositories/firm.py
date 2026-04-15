from src.models.firm import Firm

from .base import BaseRepository


class FirmRepository(BaseRepository[Firm]):
    model = Firm
