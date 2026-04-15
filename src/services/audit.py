from __future__ import annotations

from src.models import AuditEvent
from src.repositories import AuditEventRepository


class AuditEventService:
    def __init__(self, *, audit_event_repository: AuditEventRepository) -> None:
        self.audit_event_repository = audit_event_repository

    def record_event(
        self,
        *,
        workspace_id: str,
        actor_user_id: str,
        event_type: str,
        entity_type: str,
        entity_id: str,
        payload_json: dict[str, object],
    ) -> AuditEvent:
        return self.audit_event_repository.create(
            {
                "workspace_id": workspace_id,
                "actor_user_id": actor_user_id,
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "payload_json": payload_json,
            },
        )

    def list_by_workspace(
        self,
        workspace_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditEvent]:
        return self.audit_event_repository.list_by_workspace(
            workspace_id,
            limit=limit,
            offset=offset,
        )


__all__ = ["AuditEventService"]
