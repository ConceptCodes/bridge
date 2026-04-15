from __future__ import annotations

from dataclasses import dataclass

from src.errors import CONFLICT, FORBIDDEN, NOT_FOUND
from src.models import (
    AuditEvent,
    AuthenticatedUser,
    Document,
    ResearchRequest,
    User,
    Workspace,
    WorkspaceMember,
)
from src.repositories import (
    AIJobRepository,
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
    CreateResearchRequest,
    CreateWorkspaceRequest,
    ListActivityRequest,
    ListDocumentsRequest,
    ListWorkspacesRequest,
    RegisterDocumentRequest,
)

from .audit import AuditEventService
from .rbac import WorkspaceAccess, WorkspaceAuthorizationService


@dataclass(frozen=True, slots=True)
class WorkspaceDetail:
    workspace: Workspace
    member_count: int
    document_count: int
    open_research_request_count: int
    latest_ai_job_status: AIJobStatus | None


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
        audit_event_service: AuditEventService,
    ) -> None:
        self.firm_repository = firm_repository
        self.user_repository = user_repository
        self.workspace_repository = workspace_repository
        self.workspace_member_repository = workspace_member_repository
        self.document_repository = document_repository
        self.research_request_repository = research_request_repository
        self.ai_job_repository = ai_job_repository
        self.audit_event_service = audit_event_service
        self.authorization_service = WorkspaceAuthorizationService(
            workspace_repository=workspace_repository,
            workspace_member_repository=workspace_member_repository,
        )

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
        self.audit_event_service.record_event(
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
            raise CONFLICT.with_details(
                workspace_id=workspace_id,
                user_id=request.user_id,
            )

        membership = self.workspace_member_repository.create(
            {
                "workspace_id": workspace_id,
                "user_id": request.user_id,
                "role": request.role,
            },
        )
        self.audit_event_service.record_event(
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
        self.audit_event_service.record_event(
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
        self.audit_event_service.record_event(
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
        return self.audit_event_service.list_by_workspace(
            workspace_id,
            limit=request.limit,
            offset=request.offset,
        )
