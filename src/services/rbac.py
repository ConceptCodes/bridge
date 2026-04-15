from __future__ import annotations

from dataclasses import dataclass

from src.errors import FORBIDDEN, NOT_FOUND
from src.models import AuthenticatedUser, Workspace, WorkspaceMember
from src.repositories import WorkspaceMemberRepository, WorkspaceRepository
from src.schemas.enum import WorkspaceAction, WorkspaceMemberRole


ROLE_ACTIONS: dict[WorkspaceMemberRole, frozenset[WorkspaceAction]] = {
    WorkspaceMemberRole.viewer: frozenset(
        {
            WorkspaceAction.workspace_read,
            WorkspaceAction.documents_read,
            WorkspaceAction.activity_read,
            WorkspaceAction.jobs_read,
        },
    ),
    WorkspaceMemberRole.editor: frozenset(
        {
            WorkspaceAction.workspace_read,
            WorkspaceAction.workspace_update,
            WorkspaceAction.members_manage,
            WorkspaceAction.documents_read,
            WorkspaceAction.documents_create,
            WorkspaceAction.research_requests_create,
            WorkspaceAction.jobs_create,
            WorkspaceAction.jobs_read,
            WorkspaceAction.activity_read,
        },
    ),
    WorkspaceMemberRole.owner: frozenset(WorkspaceAction),
}


@dataclass(frozen=True, slots=True)
class WorkspaceAccess:
    workspace: Workspace
    membership: WorkspaceMember


class WorkspaceAuthorizationService:
    def __init__(
        self,
        *,
        workspace_repository: WorkspaceRepository,
        workspace_member_repository: WorkspaceMemberRepository,
    ) -> None:
        self.workspace_repository = workspace_repository
        self.workspace_member_repository = workspace_member_repository

    def require(
        self,
        *,
        actor: AuthenticatedUser,
        workspace_id: str,
        action: WorkspaceAction,
    ) -> WorkspaceAccess:
        workspace = self.workspace_repository.find_by_id(workspace_id)
        if workspace is None:
            raise NOT_FOUND.with_details(workspace_id=workspace_id)

        if workspace.firm_id != actor.firm_id:
            raise FORBIDDEN.with_details(
                workspace_id=workspace_id,
                actor_firm_id=actor.firm_id,
                workspace_firm_id=workspace.firm_id,
            )

        membership = self.workspace_member_repository.find_by_workspace_and_user(
            workspace_id,
            actor.user_id,
        )
        if membership is None:
            raise FORBIDDEN.with_details(
                workspace_id=workspace_id,
                user_id=actor.user_id,
                action=action.value,
            )

        allowed_actions = ROLE_ACTIONS[membership.role]
        if action not in allowed_actions:
            raise FORBIDDEN.with_details(
                workspace_id=workspace_id,
                user_id=actor.user_id,
                role=membership.role.value,
                action=action.value,
            )

        return WorkspaceAccess(workspace=workspace, membership=membership)
