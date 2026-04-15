from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
