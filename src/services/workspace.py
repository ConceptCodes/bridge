from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from src.errors import BAD_REQUEST, CONFLICT, FORBIDDEN, NOT_FOUND
from src.models import (
    AIJob,
    AuthenticatedUser,
    AuditEvent,
    Document,
    ResearchRequest,
    Workspace,
    WorkspaceMember,
    User,
)
from src.repositories import (
    AIJobRepository,
    AuditEventRepository,
    DocumentRepository,
    FirmRepository,
    ResearchRequestRepository,
    UserRepository,
    WorkspaceMemberRepository,
    WorkspaceRepository,
)
from src.schemas.enum import (
    AIJobStatus,
    ResearchRequestStatus,
    WorkspaceAction,
    WorkspaceMemberRole,
    WorkspaceStatus,
)
from src.schemas.request import (
    AddWorkspaceMemberRequest,
    CreateAIJobRequest,
    CreateResearchRequest,
    CreateWorkspaceRequest,
    ListActivityRequest,
    ListDocumentsRequest,
    ListWorkspacesRequest,
    RegisterDocumentRequest,
    UpdateAIJobStatusRequest,
)

from .rbac import WorkspaceAccess, WorkspaceAuthorizationService


@dataclass(frozen=True, slots=True)
class WorkspaceDetail:
    workspace: Workspace
    member_count: int
    document_count: int
    open_research_request_count: int
    latest_ai_job_status: AIJobStatus | None


@dataclass(frozen=True, slots=True)
class AIJobDetail:
    job: AIJob
    research_request: ResearchRequest
    workspace: Workspace


class WorkspaceService:
    def __init__(
        self,
        *,
        firm_repository: FirmRepository,
        user_repository: UserRepository,
        workspace_repository: WorkspaceRepository,
        workspace_member_repository: WorkspaceMemberRepository,
        document_repository: DocumentRepository,
        research_request_repository: ResearchRequestRepository,
        ai_job_repository: AIJobRepository,
        audit_event_repository: AuditEventRepository,
    ) -> None:
        self.firm_repository = firm_repository
        self.user_repository = user_repository
        self.workspace_repository = workspace_repository
        self.workspace_member_repository = workspace_member_repository
        self.document_repository = document_repository
        self.research_request_repository = research_request_repository
        self.ai_job_repository = ai_job_repository
        self.audit_event_repository = audit_event_repository
        self.authorization_service = WorkspaceAuthorizationService(
            workspace_repository=workspace_repository,
            workspace_member_repository=workspace_member_repository,
        )

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _require_same_actor(self, *, actor: AuthenticatedUser, user_id: str) -> None:
        if actor.user_id != user_id:
            raise FORBIDDEN.with_details(actor_user_id=actor.user_id, user_id=user_id)

    def _require_user_in_actor_firm(
        self,
        *,
        actor: AuthenticatedUser,
        user_id: str,
    ) -> User:
        user = self.user_repository.find_by_id(user_id)
        if user is None:
            raise NOT_FOUND.with_details(user_id=user_id)
        if user.firm_id != actor.firm_id:
            raise FORBIDDEN.with_details(
                user_id=user_id,
                actor_firm_id=actor.firm_id,
                user_firm_id=user.firm_id,
            )
        if not user.is_active:
            raise FORBIDDEN.with_details(user_id=user_id, reason="user_inactive")
        return user

    def _authorize_workspace(
        self,
        *,
        actor: AuthenticatedUser,
        workspace_id: str,
        action: WorkspaceAction,
    ) -> WorkspaceAccess:
        return self.authorization_service.require(
            actor=actor,
            workspace_id=workspace_id,
            action=action,
        )

    def _write_audit_event(
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

    def create_workspace(
        self,
        request: CreateWorkspaceRequest,
        *,
        actor: AuthenticatedUser,
    ) -> Workspace:
        self._require_same_actor(actor=actor, user_id=request.created_by_user_id)
        firm = self.firm_repository.find_by_id(request.firm_id)
        if firm is None:
            raise NOT_FOUND.with_details(firm_id=request.firm_id)

        creator = self.user_repository.find_by_id(request.created_by_user_id)
        if creator is None:
            raise NOT_FOUND.with_details(user_id=request.created_by_user_id)
        if creator.firm_id != request.firm_id:
            raise FORBIDDEN.with_details(
                user_id=creator.id,
                firm_id=request.firm_id,
                user_firm_id=creator.firm_id,
            )
        if not creator.is_active:
            raise FORBIDDEN.with_details(user_id=creator.id, reason="user_inactive")

        workspace = self.workspace_repository.create(
            {
                "firm_id": request.firm_id,
                "client_name": request.client_name,
                "client_external_ref": request.client_external_ref,
                "workflow_type": request.workflow_type,
                "tax_year": request.tax_year,
                "status": WorkspaceStatus.active,
                "archived_at": None,
                "created_by_user_id": request.created_by_user_id,
            },
        )
        self.workspace_member_repository.create(
            {
                "workspace_id": workspace.id,
                "user_id": request.created_by_user_id,
                "role": WorkspaceMemberRole.owner,
            },
        )
        self._write_audit_event(
            workspace_id=workspace.id,
            actor_user_id=actor.user_id,
            event_type="workspace.created",
            entity_type="workspace",
            entity_id=workspace.id,
            payload_json={
                "firm_id": request.firm_id,
                "client_name": request.client_name,
                "workflow_type": request.workflow_type.value,
                "tax_year": request.tax_year,
            },
        )
        return workspace

    def list_workspaces(
        self,
        request: ListWorkspacesRequest,
        *,
        actor: AuthenticatedUser,
    ) -> list[Workspace]:
        firm_id = request.firm_id or actor.firm_id
        if firm_id != actor.firm_id:
            raise FORBIDDEN.with_details(
                actor_firm_id=actor.firm_id,
                requested_firm_id=firm_id,
            )
        return self.workspace_repository.list_filtered(
            firm_id=firm_id,
            status=request.status,
            workflow_type=request.workflow_type,
            limit=request.limit,
            offset=request.offset,
        )

    def get_workspace_detail(
        self,
        workspace_id: str,
        *,
        actor: AuthenticatedUser,
    ) -> WorkspaceDetail:
        access = self._authorize_workspace(
            actor=actor,
            workspace_id=workspace_id,
            action=WorkspaceAction.workspace_read,
        )
        member_count = self.workspace_member_repository.count_by_workspace(workspace_id)
        document_count = self.document_repository.count_by_workspace(workspace_id)
        open_research_request_count = (
            self.research_request_repository.count_open_by_workspace(workspace_id)
        )
        latest_ai_job = self.ai_job_repository.find_latest_for_workspace(workspace_id)
        return WorkspaceDetail(
            workspace=access.workspace,
            member_count=member_count,
            document_count=document_count,
            open_research_request_count=open_research_request_count,
            latest_ai_job_status=(
                latest_ai_job.status if latest_ai_job is not None else None
            ),
        )

    def add_member(
        self,
        workspace_id: str,
        request: AddWorkspaceMemberRequest,
        *,
        actor: AuthenticatedUser,
    ) -> WorkspaceMember:
        self._authorize_workspace(
            actor=actor,
            workspace_id=workspace_id,
            action=WorkspaceAction.members_manage,
        )
        user = self._require_user_in_actor_firm(actor=actor, user_id=request.user_id)
        existing_member = self.workspace_member_repository.find_by_workspace_and_user(
            workspace_id,
            request.user_id,
        )
        if existing_member is not None:
            raise CONFLICT.with_details(workspace_id=workspace_id, user_id=request.user_id)

        membership = self.workspace_member_repository.create(
            {
                "workspace_id": workspace_id,
                "user_id": request.user_id,
                "role": request.role,
            },
        )
        self._write_audit_event(
            workspace_id=workspace_id,
            actor_user_id=actor.user_id,
            event_type="workspace.member_added",
            entity_type="workspace_member",
            entity_id=membership.id,
            payload_json={
                "user_id": user.id,
                "role": request.role.value,
            },
        )
        return membership

    def register_document(
        self,
        workspace_id: str,
        request: RegisterDocumentRequest,
        *,
        actor: AuthenticatedUser,
    ) -> Document:
        self._require_same_actor(actor=actor, user_id=request.uploaded_by_user_id)
        self._authorize_workspace(
            actor=actor,
            workspace_id=workspace_id,
            action=WorkspaceAction.documents_create,
        )
        uploader = self.user_repository.find_by_id(request.uploaded_by_user_id)
        if uploader is None:
            raise NOT_FOUND.with_details(user_id=request.uploaded_by_user_id)
        if uploader.firm_id != actor.firm_id:
            raise FORBIDDEN.with_details(
                actor_firm_id=actor.firm_id,
                user_firm_id=uploader.firm_id,
            )
        if not uploader.is_active:
            raise FORBIDDEN.with_details(user_id=uploader.id, reason="user_inactive")

        existing = self.document_repository.find_by_workspace_and_checksum(
            workspace_id,
            request.checksum,
        )
        if existing is not None:
            raise CONFLICT.with_details(
                workspace_id=workspace_id,
                checksum=request.checksum,
                existing_document_id=existing.id,
            )

        document = self.document_repository.create(
            {
                "workspace_id": workspace_id,
                "filename": request.filename,
                "document_type": request.document_type,
                "mime_type": request.mime_type,
                "storage_key": request.storage_key,
                "checksum": request.checksum,
                "size_bytes": request.size_bytes,
                "uploaded_by_user_id": request.uploaded_by_user_id,
                "status": request.status,
            },
        )
        self._write_audit_event(
            workspace_id=workspace_id,
            actor_user_id=actor.user_id,
            event_type="document.registered",
            entity_type="document",
            entity_id=document.id,
            payload_json={
                "filename": request.filename,
                "document_type": request.document_type,
                "mime_type": request.mime_type,
                "checksum": request.checksum,
            },
        )
        return document

    def list_documents(
        self,
        workspace_id: str,
        request: ListDocumentsRequest,
        *,
        actor: AuthenticatedUser,
    ) -> list[Document]:
        self._authorize_workspace(
            actor=actor,
            workspace_id=workspace_id,
            action=WorkspaceAction.documents_read,
        )
        return self.document_repository.list_by_workspace(
            workspace_id,
            document_type=request.document_type,
            status=request.status,
            created_after=request.created_after,
            created_before=request.created_before,
            limit=request.limit,
            offset=request.offset,
        )

    def create_research_request(
        self,
        workspace_id: str,
        request: CreateResearchRequest,
        *,
        actor: AuthenticatedUser,
    ) -> ResearchRequest:
        self._require_same_actor(actor=actor, user_id=request.created_by_user_id)
        access = self._authorize_workspace(
            actor=actor,
            workspace_id=workspace_id,
            action=WorkspaceAction.research_requests_create,
        )
        if access.workspace.status != WorkspaceStatus.active:
            raise FORBIDDEN.with_details(
                workspace_id=workspace_id,
                status=access.workspace.status.value,
            )

        requester = self.user_repository.find_by_id(request.created_by_user_id)
        if requester is None:
            raise NOT_FOUND.with_details(user_id=request.created_by_user_id)
        if requester.firm_id != actor.firm_id:
            raise FORBIDDEN.with_details(
                user_id=request.created_by_user_id,
                actor_firm_id=actor.firm_id,
                user_firm_id=requester.firm_id,
            )
        if (
            self.workspace_member_repository.find_by_workspace_and_user(
                workspace_id,
                request.created_by_user_id,
            )
            is None
        ):
            raise FORBIDDEN.with_details(
                workspace_id=workspace_id,
                user_id=request.created_by_user_id,
                reason="user_is_not_workspace_member",
            )

        research_request = self.research_request_repository.create(
            {
                "workspace_id": workspace_id,
                "created_by_user_id": request.created_by_user_id,
                "title": request.title,
                "question": request.question,
                "priority": request.priority,
                "status": ResearchRequestStatus.open,
            },
        )
        self._write_audit_event(
            workspace_id=workspace_id,
            actor_user_id=actor.user_id,
            event_type="research_request.created",
            entity_type="research_request",
            entity_id=research_request.id,
            payload_json={
                "title": request.title,
                "priority": request.priority,
            },
        )
        return research_request

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
        self._write_audit_event(
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

        self._write_audit_event(
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

    def list_activity(
        self,
        workspace_id: str,
        request: ListActivityRequest,
        *,
        actor: AuthenticatedUser,
    ) -> list[AuditEvent]:
        self._authorize_workspace(
            actor=actor,
            workspace_id=workspace_id,
            action=WorkspaceAction.activity_read,
        )
        return self.audit_event_repository.list_by_workspace(
            workspace_id,
            limit=request.limit,
            offset=request.offset,
        )
