from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

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
from src.schemas.enum import AIJobStatus, DocumentStatus, ResearchRequestStatus
from src.schemas.request import (
    CreateAIJobRequest,
    CreateResearchRequest,
    CreateWorkspaceRequest,
    ListActivityRequest,
    RegisterDocumentRequest,
    UpdateAIJobStatusRequest,
)
from src.services.workspace import WorkspaceService


class WorkspaceServiceIntegrationTest(unittest.TestCase):
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
        self.service = WorkspaceService(
            firm_repository=self.firm_repository,
            user_repository=self.user_repository,
            workspace_repository=self.workspace_repository,
            workspace_member_repository=self.workspace_member_repository,
            document_repository=self.document_repository,
            research_request_repository=self.research_request_repository,
            ai_job_repository=self.ai_job_repository,
            audit_event_repository=self.audit_event_repository,
        )

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_workspace_to_completed_ai_job_flow(self) -> None:
        firm = self.firm_repository.create(
            {
                "name": "Northwind Tax",
                "external_ref": "firm-001",
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

        auth_user = AuthenticatedUser(
            user_id=actor.id,
            firm_id=firm.id,
            email=actor.email,
            display_name=actor.display_name,
            global_role=actor.global_role,
            is_active=actor.is_active,
            firm_status=firm.status,
        )

        workspace = self.service.create_workspace(
            CreateWorkspaceRequest(
                firm_id=firm.id,
                client_name="Acme Corp",
                client_external_ref="acme-2026",
                workflow_type="tax_research",
                tax_year=2026,
                created_by_user_id=actor.id,
            ),
            actor=auth_user,
        )

        document = self.service.register_document(
            workspace.id,
            RegisterDocumentRequest(
                filename="engagement-letter.pdf",
                document_type="engagement_letter",
                mime_type="application/pdf",
                storage_key="docs/acme/engagement-letter.pdf",
                checksum="checksum-123",
                size_bytes=1024,
                uploaded_by_user_id=actor.id,
                status=DocumentStatus.registered,
            ),
            actor=auth_user,
        )

        research_request = self.service.create_research_request(
            workspace.id,
            CreateResearchRequest(
                created_by_user_id=actor.id,
                title="Analyze nexus exposure",
                question="Does the client have nexus in Texas for 2026?",
                priority="high",
                status=ResearchRequestStatus.open,
            ),
            actor=auth_user,
        )

        job = self.service.create_ai_job(
            research_request.id,
            CreateAIJobRequest(provider="openai", model="gpt-5.4"),
            actor=auth_user,
        )
        created_job_status = job.status
        running_job = self.service.update_ai_job_status(
            job.id,
            UpdateAIJobStatusRequest(status=AIJobStatus.running),
            actor=auth_user,
        )
        running_job_status = running_job.status
        completed_job = self.service.update_ai_job_status(
            job.id,
            UpdateAIJobStatusRequest(status=AIJobStatus.completed),
            actor=auth_user,
        )
        completed_job_status = completed_job.status
        detail = self.service.get_workspace_detail(workspace.id, actor=auth_user)
        activity = self.service.list_activity(
            workspace.id,
            ListActivityRequest(limit=20, offset=0),
            actor=auth_user,
        )

        self.assertEqual(workspace.client_name, "Acme Corp")
        self.assertEqual(document.status, DocumentStatus.registered)
        self.assertEqual(research_request.status, ResearchRequestStatus.open)
        self.assertEqual(created_job_status, AIJobStatus.queued)
        self.assertEqual(running_job_status, AIJobStatus.running)
        self.assertEqual(completed_job_status, AIJobStatus.completed)
        self.assertEqual(detail.member_count, 1)
        self.assertEqual(detail.document_count, 1)
        self.assertEqual(detail.open_research_request_count, 1)
        self.assertEqual(detail.latest_ai_job_status, AIJobStatus.completed)
        self.assertEqual(len(activity), 6)
        event_types = [event.event_type for event in activity]
        self.assertEqual(event_types.count("ai_job.status_changed"), 2)
        self.assertIn("workspace.created", event_types)
        self.assertIn("document.registered", event_types)
        self.assertIn("research_request.created", event_types)
        self.assertIn("ai_job.created", event_types)


if __name__ == "__main__":
    unittest.main()
