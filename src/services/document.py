from __future__ import annotations

from dataclasses import dataclass

from src.errors import CONFLICT, FORBIDDEN, NOT_FOUND
from src.models import AuthenticatedUser, Document
from src.repositories import (
    DocumentRepository,
    UserRepository,
    WorkspaceMemberRepository,
    WorkspaceRepository,
)
from src.schemas.enum import WorkspaceAction, WorkspaceStatus
from src.schemas.request import ListDocumentsRequest, RegisterDocumentRequest
from src.storage.documents import DocumentStorage, LocalDocumentStorage

from .audit import AuditEventService
from .rbac import WorkspaceAuthorizationService


@dataclass(frozen=True, slots=True)
class DocumentUploadResult:
    document: Document
    storage_key: str


class DocumentService:
    def __init__(
        self,
        *,
        workspace_repository: WorkspaceRepository,
        workspace_member_repository: WorkspaceMemberRepository,
        user_repository: UserRepository,
        document_repository: DocumentRepository,
        audit_event_service: AuditEventService,
        storage: DocumentStorage | None = None,
    ) -> None:
        self.workspace_repository = workspace_repository
        self.workspace_member_repository = workspace_member_repository
        self.user_repository = user_repository
        self.document_repository = document_repository
        self.audit_event_service = audit_event_service
        self.storage = storage or LocalDocumentStorage()
        self.authorization_service = WorkspaceAuthorizationService(
            workspace_repository=workspace_repository,
            workspace_member_repository=workspace_member_repository,
        )

    def register_document(
        self,
        workspace_id: str,
        request: RegisterDocumentRequest,
        *,
        actor: AuthenticatedUser,
        content: bytes,
    ) -> DocumentUploadResult:
        if actor.user_id != request.uploaded_by_user_id:
            raise FORBIDDEN.with_details(
                actor_user_id=actor.user_id,
                user_id=request.uploaded_by_user_id,
            )

        access = self.authorization_service.require(
            actor=actor,
            workspace_id=workspace_id,
            action=WorkspaceAction.documents_create,
        )
        if access.workspace.status != WorkspaceStatus.active:
            raise FORBIDDEN.with_details(
                workspace_id=workspace_id,
                status=access.workspace.status.value,
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

        stored = self.storage.save(request.storage_key, content)
        document = self.document_repository.create(
            {
                "workspace_id": workspace_id,
                "filename": request.filename,
                "document_type": request.document_type,
                "mime_type": request.mime_type,
                "storage_key": stored.storage_key,
                "checksum": request.checksum,
                "size_bytes": stored.size_bytes,
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
                "filename": document.filename,
                "document_type": document.document_type,
                "mime_type": document.mime_type,
                "checksum": document.checksum,
                "status": document.status.value,
            },
        )
        return DocumentUploadResult(document=document, storage_key=stored.storage_key)

    def list_documents(
        self,
        workspace_id: str,
        request: ListDocumentsRequest,
        *,
        actor: AuthenticatedUser,
    ) -> list[Document]:
        self.authorization_service.require(
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
