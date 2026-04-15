from __future__ import annotations

import tempfile
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.config import Settings
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
from src.schemas.enum import DocumentStatus
from src.schemas.request import CreateWorkspaceRequest, RegisterDocumentRequest
from src.services.audit import AuditEventService
from src.services.document import DocumentService
from src.services.workspace import WorkspaceService
from src.storage.documents import LocalDocumentStorage


class DocumentServiceIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
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

        storage = LocalDocumentStorage(
            Settings(
                document_storage_root=self.tempdir.name,
                database_url="sqlite+pysqlite://",
            ),
        )
        self.document_service = DocumentService(
            workspace_repository=self.workspace_repository,
            workspace_member_repository=self.workspace_member_repository,
            user_repository=self.user_repository,
            document_repository=self.document_repository,
            audit_event_service=self.audit_event_service,
            storage=storage,
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

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        self.tempdir.cleanup()

    def test_register_document_persists_file_and_row(self) -> None:
        firm = self.firm_repository.create(
            {
                "name": "Northwind Tax",
                "external_ref": "firm-002",
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
        workspace = self.workspace_service.create_workspace(
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

        result = self.document_service.register_document(
            workspace.id,
            RegisterDocumentRequest(
                filename="engagement-letter.pdf",
                document_type="engagement_letter",
                mime_type="application/pdf",
                storage_key="documents/acme/engagement-letter.pdf",
                checksum="checksum-abc",
                size_bytes=1024,
                uploaded_by_user_id=actor.id,
                status=DocumentStatus.registered,
            ),
            actor=auth_user,
            content=b"pdf-bytes",
        )

        self.assertEqual(
            self.document_service.storage.read(
                "documents/acme/engagement-letter.pdf",
            ),
            b"pdf-bytes",
        )
        self.assertEqual(result.document.status, DocumentStatus.registered)
        self.assertEqual(result.storage_key, "documents/acme/engagement-letter.pdf")
        self.assertEqual(
            self.document_repository.find_by_workspace_and_checksum(
                workspace.id,
                "checksum-abc",
            ).id,
            result.document.id,
        )


if __name__ == "__main__":
    unittest.main()
