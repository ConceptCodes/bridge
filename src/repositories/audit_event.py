from src.models.audit_event import AuditEvent

from .base import BaseRepository


class AuditEventRepository(BaseRepository[AuditEvent]):
    model = AuditEvent
