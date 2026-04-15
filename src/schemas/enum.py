from __future__ import annotations

from enum import StrEnum


class FirmStatus(StrEnum):
    active = "active"
    archived = "archived"


class WorkspaceStatus(StrEnum):
    active = "active"
    archived = "archived"


class WorkflowType(StrEnum):
    tax_research = "tax_research"
    tax_filing = "tax_filing"
    audit_support = "audit_support"


class WorkspaceMemberRole(StrEnum):
    owner = "owner"
    editor = "editor"
    viewer = "viewer"


class WorkspaceAction(StrEnum):
    workspace_read = "workspace.read"
    workspace_update = "workspace.update"
    members_manage = "members.manage"
    documents_read = "documents.read"
    documents_create = "documents.create"
    research_requests_create = "research_requests.create"
    jobs_create = "jobs.create"
    jobs_update_status = "jobs.update_status"
    jobs_read = "jobs.read"
    activity_read = "activity.read"


class DocumentStatus(StrEnum):
    registered = "registered"
    processing = "processing"
    available = "available"
    failed = "failed"


class ResearchRequestStatus(StrEnum):
    open = "open"
    queued = "queued"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class AIJobStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
