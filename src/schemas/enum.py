from __future__ import annotations

from enum import Enum


class FirmStatus(str, Enum):
    active = "active"
    archived = "archived"
