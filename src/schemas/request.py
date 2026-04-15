from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.schemas.enum import (
    AIJobStatus,
    DocumentStatus,
    ResearchRequestStatus,
    WorkspaceMemberRole,
    WorkspaceStatus,
    WorkflowType,
)


class RequestSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class CreateWorkspaceRequest(RequestSchema):
    firm_id: str = Field(min_length=1, max_length=36)
    client_name: str = Field(min_length=1, max_length=255)
    client_external_ref: str | None = Field(default=None, min_length=1, max_length=255)
    workflow_type: WorkflowType
    tax_year: int = Field(ge=1900, le=2100)
    created_by_user_id: str = Field(min_length=1, max_length=36)


class ListWorkspacesRequest(RequestSchema):
    firm_id: str | None = Field(default=None, min_length=1, max_length=36)
    status: WorkspaceStatus | None = None
    workflow_type: WorkflowType | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class AddWorkspaceMemberRequest(RequestSchema):
    user_id: str = Field(min_length=1, max_length=36)
    role: WorkspaceMemberRole


class RegisterDocumentRequest(RequestSchema):
    filename: str = Field(min_length=1, max_length=255)
    document_type: str = Field(min_length=1, max_length=100)
    mime_type: str = Field(min_length=1, max_length=100)
    storage_key: str = Field(min_length=1, max_length=512)
    checksum: str = Field(min_length=1, max_length=128)
    size_bytes: int = Field(ge=0)
    uploaded_by_user_id: str = Field(min_length=1, max_length=36)
    status: DocumentStatus = DocumentStatus.registered


class ListDocumentsRequest(RequestSchema):
    document_type: str | None = Field(default=None, min_length=1, max_length=100)
    status: DocumentStatus | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_created_range(self) -> ListDocumentsRequest:
        if (
            self.created_after is not None
            and self.created_before is not None
            and self.created_before < self.created_after
        ):
            raise ValueError("created_before must be greater than or equal to created_after.")
        return self


class CreateResearchRequest(RequestSchema):
    created_by_user_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=1, max_length=255)
    question: str = Field(min_length=1, max_length=4000)
    priority: str = Field(min_length=1, max_length=50)
    status: ResearchRequestStatus = ResearchRequestStatus.open


class CreateAIJobRequest(RequestSchema):
    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)


class UpdateAIJobStatusRequest(RequestSchema):
    status: AIJobStatus


class ListActivityRequest(RequestSchema):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
