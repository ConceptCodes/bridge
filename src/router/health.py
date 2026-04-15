from __future__ import annotations

from fastapi import APIRouter

from src.schemas.response import ApiResponse, HealthData

health_router = APIRouter(tags=["health"])


@health_router.get(
    "/health",
    response_model=ApiResponse[HealthData],
    summary="Health check",
)
async def health() -> ApiResponse[HealthData]:
    return ApiResponse(data=HealthData())


@health_router.get(
    "/healthz",
    response_model=ApiResponse[HealthData],
    include_in_schema=False,
)
async def healthz() -> ApiResponse[HealthData]:
    return ApiResponse(data=HealthData())
