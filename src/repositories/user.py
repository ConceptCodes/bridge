from src.models.user import User

from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User
