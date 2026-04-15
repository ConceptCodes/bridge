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
