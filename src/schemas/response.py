from __future__ import annotations

from pydantic import BaseModel


class ApiResponse[T](BaseModel):
    message: str = "Operation successful"
    data: T | None = None


class HealthData(BaseModel):
    status: str = "ok"
