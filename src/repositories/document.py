from src.models.document import Document

from .base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    model = Document
