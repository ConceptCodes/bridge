from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SQLITE_PATH = Path("database.db")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default_factory=lambda: f"sqlite:///{DEFAULT_SQLITE_PATH}",
        validation_alias="DATABASE_URL",
    )
    sqlalchemy_echo: bool = Field(default=False, validation_alias="SQLALCHEMY_ECHO")
    pool_pre_ping: bool = Field(
        default=True,
        validation_alias=AliasChoices("SQLALCHEMY_POOL_PRE_PING", "POOL_PRE_PING"),
    )
    auth_secret_key: str = Field(default="", validation_alias="AUTH_SECRET_KEY")
    auth_issuer: str = Field(default="bridge", validation_alias="AUTH_ISSUER")
    auth_audience: str = Field(default="bridge-api", validation_alias="AUTH_AUDIENCE")
    auth_access_token_ttl_minutes: int = Field(
        default=60 * 24,
        validation_alias="AUTH_ACCESS_TOKEN_TTL_MINUTES",
    )
    auth_clock_skew_seconds: int = Field(
        default=30,
        validation_alias="AUTH_CLOCK_SKEW_SECONDS",
    )
    auth_required: bool = Field(default=True, validation_alias="AUTH_REQUIRED")
    auth_public_path_prefixes: tuple[str, ...] = Field(
        default=(
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/health",
            "/api/healthz",
        ),
        validation_alias="AUTH_PUBLIC_PATH_PREFIXES",
    )
    cors_allow_origins: tuple[str, ...] = Field(
        default=("*",),
        validation_alias="CORS_ALLOW_ORIGINS",
    )
    cors_allow_methods: tuple[str, ...] = Field(
        default=("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"),
        validation_alias="CORS_ALLOW_METHODS",
    )
    cors_allow_headers: tuple[str, ...] = Field(
        default=("*",),
        validation_alias="CORS_ALLOW_HEADERS",
    )
    cors_allow_credentials: bool = Field(
        default=False,
        validation_alias="CORS_ALLOW_CREDENTIALS",
    )
    cors_max_age: int = Field(default=600, validation_alias="CORS_MAX_AGE")
    content_type_allowed_types: tuple[str, ...] = Field(
        default=(
            "application/json",
            "application/*+json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
        ),
        validation_alias="CONTENT_TYPE_ALLOWED_TYPES",
    )
    content_type_body_methods: tuple[str, ...] = Field(
        default=("POST", "PUT", "PATCH", "DELETE"),
        validation_alias="CONTENT_TYPE_BODY_METHODS",
    )

    @field_validator(
        "cors_allow_origins",
        "cors_allow_methods",
        "cors_allow_headers",
        "auth_public_path_prefixes",
        "content_type_allowed_types",
        "content_type_body_methods",
        mode="before",
    )
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if value is None or value == "":
            return value
        if isinstance(value, str):
            return tuple(
                item.strip() for item in value.split(",") if item.strip()
            )
        if isinstance(value, Sequence):
            return tuple(value)
        return value

    @field_validator("cors_allow_methods", "content_type_body_methods")
    @classmethod
    def _normalize_methods(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(method.upper() for method in value)

    @field_validator("content_type_allowed_types")
    @classmethod
    def _normalize_content_types(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(content_type.lower() for content_type in value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


__all__ = [
    "DEFAULT_SQLITE_PATH",
    "Settings",
    "get_settings",
]
