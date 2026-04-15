from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.errors import BAD_REQUEST, CONFLICT, AppError
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
from src.schemas.enum import AIJobStatus, ResearchRequestStatus
from src.schemas.request import (
    CreateAIJobRequest,
    CreateResearchRequest,
    CreateWorkspaceRequest,
    UpdateAIJobStatusRequest,
)
from src.services.ai_job import AIJobService
from src.services.audit import AuditEventService
from src.services.research_request import ResearchRequestService
from src.services.workspace import WorkspaceService


class AIJobServiceIntegrationTest(unittest.TestCase):
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
        self.research_request_service = ResearchRequestService(
            workspace_repository=self.workspace_repository,
            workspace_member_repository=self.workspace_member_repository,
            user_repository=self.user_repository,
            research_request_repository=self.research_request_repository,
            audit_event_service=self.audit_event_service,
        )
        self.ai_job_service = AIJobService(
            workspace_repository=self.workspace_repository,
            workspace_member_repository=self.workspace_member_repository,
            research_request_repository=self.research_request_repository,
            ai_job_repository=self.ai_job_repository,
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
        return auth_user, actor.id

    def _create_workspace_and_request(
        self,
        auth_user: AuthenticatedUser,
        actor_id: str,
    ) -> str:
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
        research_request = self.research_request_service.create_research_request(
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
        return research_request.id

    def test_create_update_and_read_ai_job(self) -> None:
        auth_user, actor_id = self._create_actor()
        research_request_id = self._create_workspace_and_request(auth_user, actor_id)

        job = self.ai_job_service.create_ai_job(
            research_request_id,
            CreateAIJobRequest(provider="openai", model="gpt-5.4"),
            actor=auth_user,
        )
        detail = self.ai_job_service.get_ai_job_detail(job.id, actor=auth_user)
        self.assertEqual(detail.job.status, AIJobStatus.queued)
        running_job = self.ai_job_service.update_ai_job_status(
            job.id,
            UpdateAIJobStatusRequest(status=AIJobStatus.running),
            actor=auth_user,
        )
        running_status = running_job.status
        completed_job = self.ai_job_service.update_ai_job_status(
            job.id,
            UpdateAIJobStatusRequest(status=AIJobStatus.completed),
            actor=auth_user,
        )
        completed_status = completed_job.status

        self.assertEqual(detail.job.id, job.id)
        self.assertEqual(detail.research_request.id, research_request_id)
        self.assertEqual(running_status, AIJobStatus.running)
        self.assertEqual(completed_status, AIJobStatus.completed)
        self.assertEqual(completed_job.attempt_count, 1)
        self.assertIsNotNone(completed_job.started_at)
        self.assertIsNotNone(completed_job.completed_at)

    def test_rejects_duplicate_active_job(self) -> None:
        auth_user, actor_id = self._create_actor()
        research_request_id = self._create_workspace_and_request(auth_user, actor_id)

        first_job = self.ai_job_service.create_ai_job(
            research_request_id,
            CreateAIJobRequest(provider="openai", model="gpt-5.4"),
            actor=auth_user,
        )

        with self.assertRaises(AppError) as cm:
            self.ai_job_service.create_ai_job(
                research_request_id,
                CreateAIJobRequest(provider="openai", model="gpt-5.4"),
                actor=auth_user,
            )

        self.assertEqual(cm.exception.code, CONFLICT.code)
        self.assertEqual(
            cm.exception.details["active_job_id"],
            first_job.id,
        )

    def test_rejects_invalid_status_transition(self) -> None:
        auth_user, actor_id = self._create_actor()
        research_request_id = self._create_workspace_and_request(auth_user, actor_id)

        job = self.ai_job_service.create_ai_job(
            research_request_id,
            CreateAIJobRequest(provider="openai", model="gpt-5.4"),
            actor=auth_user,
        )

        with self.assertRaises(AppError) as cm:
            self.ai_job_service.update_ai_job_status(
                job.id,
                UpdateAIJobStatusRequest(status=AIJobStatus.completed),
                actor=auth_user,
            )

        self.assertEqual(cm.exception.code, BAD_REQUEST.code)
        self.assertEqual(
            cm.exception.details["current_status"],
            AIJobStatus.queued.value,
        )
        self.assertEqual(
            cm.exception.details["requested_status"],
            AIJobStatus.completed.value,
        )


if __name__ == "__main__":
    unittest.main()
