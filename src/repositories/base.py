from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository[ModelT]:
    """Generic CRUD helpers for SQLAlchemy models."""

    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def find_by_id(self, entity_id: str) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def find_all(self) -> list[ModelT]:
        statement = select(self.model).order_by(self.model.created_at, self.model.id)
        return list(self.session.scalars(statement).all())

    def create(self, data: Mapping[str, Any]) -> ModelT:
        entity = self.model(**self._sanitize_payload(data))
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(self, entity_id: str, data: Mapping[str, Any]) -> ModelT | None:
        entity = self.find_by_id(entity_id)
        if entity is None:
            return None

        for field_name, value in self._sanitize_payload(data).items():
            setattr(entity, field_name, value)

        self.session.flush()
        return entity

    def delete(self, entity_id: str) -> bool:
        entity = self.find_by_id(entity_id)
        if entity is None:
            return False

        self.session.delete(entity)
        self.session.flush()
        return True

    def _sanitize_payload(self, data: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        payload.pop("id", None)
        payload.pop("created_at", None)
        payload.pop("updated_at", None)
        return payload
