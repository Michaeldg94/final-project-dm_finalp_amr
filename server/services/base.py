"""Base classes for the service layer (sync + async helpers)."""

from typing import Any, Generic, Optional, Sequence, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from sqlalchemy.sql import Select

# Generic type variable for SQLAlchemy ORM models
T = TypeVar("T")


class BaseService:
    """Base class for service objects that use an **async** SQLAlchemy session.

    Store the provided `AsyncSession` on `self.session` for use in methods.
    """

    def __init__(self, session: AsyncSession):
        """Initialize the service with an async DB session.

        Args:
            session: An active `AsyncSession`.
        """
        self.session: AsyncSession = session


class BaseDataManager(Generic[T]):
    """Lightweight helper for common **sync** SQLAlchemy query patterns.

    Use this with a regular `Session` (not `AsyncSession`).
    """

    def __init__(self, session: Session):
        """Initialize the data manager with a sync DB session.

        Args:
            session: An active `Session`.
        """
        self.session: Session = session

    def get_one(self, stmt: Select[Any]) -> Optional[T]:
        """Execute a statement and return a single object or None.

        Args:
            stmt: A SQLAlchemy `Select` constructed for the target model.

        Returns:
            The single ORM object or `None` if not found.
        """
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    def get_all(self, stmt: Select[Any]) -> Sequence[T]:
        """Execute a statement and return all matching objects.

        Args:
            stmt: A SQLAlchemy `Select` constructed for the target model.

        Returns:
            A sequence of ORM objects (could be empty).
        """
        result = self.session.execute(stmt)
        return result.scalars().all()