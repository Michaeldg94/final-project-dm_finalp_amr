"""SQLAlchemy session management for PostgreSQL."""

import contextlib
from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from server.backend.config import config


class PostgresSessionManager:
    """Create and manage a SQLAlchemy Engine and session factory.

    Use `open_session()` as a context manager to get a `Session`
    with automatic commit/rollback handling.
    """
    def __init__(self, engine_kwargs: dict[str, Any] | None = None):

        """Initialize the engine and session factory.

        Args:
            engine_kwargs: Extra kwargs passed to `create_engine`, e.g.
                {"pool_pre_ping": True, "pool_size": 5}.
        """
    
        if engine_kwargs is None:
            engine_kwargs = {}
        self.engine = create_engine(config.postgres_dns, **engine_kwargs)
        #self.engine = create_engine(config.postgres_dns, **engine_kwargs, echo=True, future=True)    # this logs all SQL statements to stdout
        self.sessionmaker = sessionmaker(
            autocommit = False,
            bind=self.engine,
            autoflush = False,
            expire_on_commit = False,
        )

    def close(self):
        """Dispose the engine and disable the session factory.

        After calling this, the manager becomes unusable until re-created.
        """
        if self.engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        self.engine.dispose()

        self.engine = None
        self.sessionmaker = None

    @contextlib.contextmanager
    def open_session(self) -> Generator[Session, None, None]:
        """Context manager that yields a `Session` and handles commit/rollback.

        Yields:
            A live SQLAlchemy `Session`.

        Raises:
           RuntimeError: If called after the manager has been closed.
            Exception: Re-raised from the session block after rollback.
        """
        if self.sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self.sessionmaker()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
session_manager = PostgresSessionManager()

def get_db():
    """FastAPI dependency that yields a database session."""
    with session_manager.open_session() as session:
        yield session