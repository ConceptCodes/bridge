from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from src.errors import BAD_REQUEST, CONFLICT, FORBIDDEN, NOT_FOUND
from src.models import AIJob, AuthenticatedUser, ResearchRequest, Workspace
from src.repositories import (
    AIJobRepository,
    ResearchRequestRepository,
    WorkspaceMemberRepository,
    WorkspaceRepository,
)
from src.schemas.enum import (
    AIJobStatus,
    WorkspaceAction,
    WorkspaceMemberRole,
    WorkspaceStatus,
)
from src.schemas.request import CreateAIJobRequest, UpdateAIJobStatusRequest

from .audit import AuditEventService
from .rbac import WorkspaceAuthorizationService


@dataclass(frozen=True, slots=True)
class AIJobDetail:
    job: AIJob
    research_request: ResearchRequest
    workspace: Workspace


class AIJobService:
    def __init__(
        self,
        *,
        workspace_repository: WorkspaceRepository,
        workspace_member_repository: WorkspaceMemberRepository,
        research_request_repository: ResearchRequestRepository,
        ai_job_repository: AIJobRepository,
        audit_event_service: AuditEventService,
    ) -> None:
        self.workspace_repository = workspace_repository
        self.workspace_member_repository = workspace_member_repository
        self.research_request_repository = research_request_repository
        self.ai_job_repository = ai_job_repository
        self.audit_event_service = audit_event_service
        self.authorization_service = WorkspaceAuthorizationService(
            workspace_repository=workspace_repository,
            workspace_member_repository=workspace_member_repository,
        )

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _authorize_workspace(
        self,
        *,
        actor: AuthenticatedUser,
        workspace_id: str,
        action: WorkspaceAction,
    ):
        return self.authorization_service.require(
            actor=actor,
            workspace_id=workspace_id,
            action=action,
        )

    def create_ai_job(
        self,
        research_request_id: str,
        request: CreateAIJobRequest,
        *,
        actor: AuthenticatedUser,
    ) -> AIJob:
        research_request = self.research_request_repository.find_by_id(
            research_request_id,
        )
        if research_request is None:
            raise NOT_FOUND.with_details(research_request_id=research_request_id)

        access = self._authorize_workspace(
            actor=actor,
            workspace_id=research_request.workspace_id,
            action=WorkspaceAction.jobs_create,
        )
        if access.workspace.status != WorkspaceStatus.active:
            raise FORBIDDEN.with_details(
                workspace_id=research_request.workspace_id,
                status=access.workspace.status.value,
            )

        active_job = self.ai_job_repository.find_by_research_request_and_active_status(
            research_request_id,
        )
        if active_job is not None:
            raise CONFLICT.with_details(
                research_request_id=research_request_id,
                active_job_id=active_job.id,
            )

        job = self.ai_job_repository.create(
            {
                "research_request_id": research_request_id,
                "provider": request.provider,
                "model": request.model,
                "status": AIJobStatus.queued,
                "attempt_count": 0,
                "queued_at": self._now(),
                "started_at": None,
                "completed_at": None,
                "error_code": None,
                "error_message": None,
            },
        )
        self.audit_event_service.record_event(
            workspace_id=research_request.workspace_id,
            actor_user_id=actor.user_id,
            event_type="ai_job.created",
            entity_type="ai_job",
            entity_id=job.id,
            payload_json={
                "provider": request.provider,
                "model": request.model,
                "status": job.status.value,
            },
        )
        return job

    def update_ai_job_status(
        self,
        job_id: str,
        request: UpdateAIJobStatusRequest,
        *,
        actor: AuthenticatedUser,
    ) -> AIJob:
        job = self.ai_job_repository.find_by_id(job_id)
        if job is None:
            raise NOT_FOUND.with_details(job_id=job_id)
        previous_status = job.status

        research_request = self.research_request_repository.find_by_id(
            job.research_request_id,
        )
        if research_request is None:
            raise NOT_FOUND.with_details(research_request_id=job.research_request_id)

        access = self._authorize_workspace(
            actor=actor,
            workspace_id=research_request.workspace_id,
            action=WorkspaceAction.jobs_update_status,
        )
        if access.membership.role != WorkspaceMemberRole.owner:
            raise FORBIDDEN.with_details(
                workspace_id=research_request.workspace_id,
                role=access.membership.role.value,
                action=request.status.value,
            )

        transition_key = (job.status, request.status)
        allowed_transitions: dict[tuple[AIJobStatus, AIJobStatus], None] = {
            (AIJobStatus.queued, AIJobStatus.running): None,
            (AIJobStatus.running, AIJobStatus.completed): None,
            (AIJobStatus.running, AIJobStatus.failed): None,
            (AIJobStatus.queued, AIJobStatus.cancelled): None,
            (AIJobStatus.running, AIJobStatus.cancelled): None,
        }
        if transition_key not in allowed_transitions:
            raise BAD_REQUEST.with_details(
                job_id=job_id,
                current_status=previous_status.value,
                requested_status=request.status.value,
            )

        now = self._now()
        updates: dict[str, object] = {"status": request.status}
        if transition_key == (AIJobStatus.queued, AIJobStatus.running):
            updates["started_at"] = now
            updates["attempt_count"] = job.attempt_count + 1
            updates["error_code"] = None
            updates["error_message"] = None
        elif request.status == AIJobStatus.completed:
            updates["completed_at"] = now
            updates["error_code"] = None
            updates["error_message"] = None
        elif request.status == AIJobStatus.failed:
            updates["completed_at"] = now
            updates["error_code"] = job.error_code or "job_failed"
            updates["error_message"] = job.error_message or "The job failed."
        elif request.status == AIJobStatus.cancelled:
            updates["completed_at"] = now

        updated = self.ai_job_repository.update(job_id, updates)
        if updated is None:
            raise NOT_FOUND.with_details(job_id=job_id)

        self.audit_event_service.record_event(
            workspace_id=research_request.workspace_id,
            actor_user_id=actor.user_id,
            event_type="ai_job.status_changed",
            entity_type="ai_job",
            entity_id=job_id,
            payload_json={
                "from_status": previous_status.value,
                "to_status": request.status.value,
            },
        )
        return updated

    def get_ai_job_detail(
        self,
        job_id: str,
        *,
        actor: AuthenticatedUser,
    ) -> AIJobDetail:
        job = self.ai_job_repository.find_by_id(job_id)
        if job is None:
            raise NOT_FOUND.with_details(job_id=job_id)

        research_request = self.research_request_repository.find_by_id(
            job.research_request_id,
        )
        if research_request is None:
            raise NOT_FOUND.with_details(research_request_id=job.research_request_id)

        access = self._authorize_workspace(
            actor=actor,
            workspace_id=research_request.workspace_id,
            action=WorkspaceAction.jobs_read,
        )
        return AIJobDetail(
            job=job,
            research_request=research_request,
            workspace=access.workspace,
        )


__all__ = ["AIJobDetail", "AIJobService"]
