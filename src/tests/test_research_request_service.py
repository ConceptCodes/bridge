from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.errors import AppError
from src.models import AuthenticatedUser, Base
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
from src.schemas.enum import ResearchRequestStatus
from src.schemas.request import CreateResearchRequest, CreateWorkspaceRequest
from src.services.audit import AuditEventService
from src.services.research_request import ResearchRequestService
from src.services.workspace import WorkspaceService


class ResearchRequestServiceIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )
        self.session: Session = self.session_factory()

        self.firm_repository = FirmRepository(self.session)
        self.user_repository = UserRepository(self.session)
        self.workspace_repository = WorkspaceRepository(self.session)
        self.workspace_member_repository = WorkspaceMemberRepository(self.session)
        self.document_repository = DocumentRepository(self.session)
        self.research_request_repository = ResearchRequestRepository(self.session)
        self.ai_job_repository = AIJobRepository(self.session)
        self.audit_event_repository = AuditEventRepository(self.session)
        self.audit_event_service = AuditEventService(
            audit_event_repository=self.audit_event_repository,
        )
        self.workspace_service = WorkspaceService(
            firm_repository=self.firm_repository,
            user_repository=self.user_repository,
            workspace_repository=self.workspace_repository,
            workspace_member_repository=self.workspace_member_repository,
            document_repository=self.document_repository,
            research_request_repository=self.research_request_repository,
            ai_job_repository=self.ai_job_repository,
            audit_event_service=self.audit_event_service,
        )
        self.service = ResearchRequestService(
            workspace_repository=self.workspace_repository,
            workspace_member_repository=self.workspace_member_repository,
            user_repository=self.user_repository,
            research_request_repository=self.research_request_repository,
            audit_event_service=self.audit_event_service,
        )

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _create_actor(self) -> tuple[AuthenticatedUser, str]:
        firm = self.firm_repository.create(
            {
                "name": "Northwind Tax",
                "external_ref": "firm-003",
                "status": "active",
            },
        )
        actor = self.user_repository.create(
            {
                "firm_id": firm.id,
                "email": "owner@example.com",
                "display_name": "Owner",
                "global_role": "firm_admin",
                "is_active": True,
            },
        )
        self.session.flush()
        return (
            AuthenticatedUser(
                user_id=actor.id,
                firm_id=firm.id,
                email=actor.email,
                display_name=actor.display_name,
                global_role=actor.global_role,
                is_active=actor.is_active,
                firm_status=firm.status,
            ),
            actor.id,
        )

    def test_create_research_request_records_audit_event(self) -> None:
        auth_user, actor_id = self._create_actor()
        workspace = self.workspace_service.create_workspace(
            CreateWorkspaceRequest(
                firm_id=auth_user.firm_id,
                client_name="Acme Corp",
                client_external_ref="acme-2026",
                workflow_type="tax_research",
                tax_year=2026,
                created_by_user_id=actor_id,
            ),
            actor=auth_user,
        )
        request = self.service.create_research_request(
            workspace.id,
            CreateResearchRequest(
                created_by_user_id=actor_id,
                title="Analyze nexus exposure",
                question="Does the client have nexus in Texas for 2026?",
                priority="high",
                status=ResearchRequestStatus.open,
            ),
            actor=auth_user,
        )

        events = self.audit_event_repository.list_by_workspace(workspace.id)
        self.assertEqual(request.status, ResearchRequestStatus.open)
        self.assertEqual(len(events), 2)
        self.assertIn(
            "research_request.created",
            [event.event_type for event in events],
        )

    def test_rejects_non_member_requester(self) -> None:
        auth_user, actor_id = self._create_actor()
        workspace = self.workspace_service.create_workspace(
            CreateWorkspaceRequest(
                firm_id=auth_user.firm_id,
                client_name="Acme Corp",
                client_external_ref="acme-2026",
                workflow_type="tax_research",
                tax_year=2026,
                created_by_user_id=actor_id,
            ),
            actor=auth_user,
        )
        outsider = self.user_repository.create(
            {
                "firm_id": auth_user.firm_id,
                "email": "outsider@example.com",
                "display_name": "Outsider",
                "global_role": "firm_admin",
                "is_active": True,
            },
        )
        self.session.flush()

        outsider_auth = AuthenticatedUser(
            user_id=outsider.id,
            firm_id=auth_user.firm_id,
            email=outsider.email,
            display_name=outsider.display_name,
            global_role=outsider.global_role,
            is_active=outsider.is_active,
            firm_status=auth_user.firm_status,
        )

        with self.assertRaises(AppError):
            self.service.create_research_request(
                workspace.id,
                CreateResearchRequest(
                    created_by_user_id=outsider.id,
                    title="Should fail",
                    question="No membership",
                    priority="low",
                    status=ResearchRequestStatus.open,
                ),
                actor=outsider_auth,
            )


if __name__ == "__main__":
    unittest.main()
