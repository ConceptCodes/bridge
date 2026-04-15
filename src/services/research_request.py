from __future__ import annotations

from src.errors import FORBIDDEN, NOT_FOUND
from src.models import AuthenticatedUser, ResearchRequest
from src.repositories import (
    ResearchRequestRepository,
    UserRepository,
    WorkspaceMemberRepository,
    WorkspaceRepository,
)
from src.schemas.enum import ResearchRequestStatus, WorkspaceAction, WorkspaceStatus
from src.schemas.request import CreateResearchRequest

from .audit import AuditEventService
from .rbac import WorkspaceAuthorizationService


class ResearchRequestService:
    def __init__(
        self,
        *,
        workspace_repository: WorkspaceRepository,
        workspace_member_repository: WorkspaceMemberRepository,
        user_repository: UserRepository,
        research_request_repository: ResearchRequestRepository,
        audit_event_service: AuditEventService,
    ) -> None:
        self.workspace_repository = workspace_repository
        self.workspace_member_repository = workspace_member_repository
        self.user_repository = user_repository
        self.research_request_repository = research_request_repository
        self.audit_event_service = audit_event_service
        self.authorization_service = WorkspaceAuthorizationService(
            workspace_repository=workspace_repository,
            workspace_member_repository=workspace_member_repository,
        )

    def _require_same_actor(self, *, actor: AuthenticatedUser, user_id: str) -> None:
        if actor.user_id != user_id:
            raise FORBIDDEN.with_details(actor_user_id=actor.user_id, user_id=user_id)

    def create_research_request(
        self,
        workspace_id: str,
        request: CreateResearchRequest,
        *,
        actor: AuthenticatedUser,
    ) -> ResearchRequest:
        self._require_same_actor(actor=actor, user_id=request.created_by_user_id)
        access = self.authorization_service.require(
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


__all__ = ["ResearchRequestService"]
