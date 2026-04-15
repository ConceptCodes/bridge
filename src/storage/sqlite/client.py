from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import Settings, get_settings
from src.logger import get_logger


logger = get_logger(__name__)


class DatabaseClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            # Lazy initialization keeps the module importable without a live DB.
            logger.debug("Creating SQLAlchemy engine for %s", self.settings.database_url)
            connect_args = {}
            if self.settings.database_url.startswith("sqlite"):
                connect_args["check_same_thread"] = False
            self._engine = create_engine(
                self.settings.database_url,
                echo=self.settings.sqlalchemy_echo,
                pool_pre_ping=self.settings.pool_pre_ping,
                connect_args=connect_args,
            )
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        if self._session_factory is None:
            logger.debug("Creating SQLAlchemy session factory")
            self._session_factory = sessionmaker(
                bind=self.engine,
                autoflush=False,
                expire_on_commit=False,
            )
        return self._session_factory

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()


database_client = DatabaseClient()
