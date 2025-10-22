from typing import Any, Generic, Optional, Sequence, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from sqlalchemy.sql import Select

# Define un tipo genérico para representar cualquier modelo SQLAlchemy
T = TypeVar("T")


class BaseService:
    """
    Clase base para todos los servicios.
    Encapsula la sesión de base de datos.
    """

    def __init__(self, session: AsyncSession):
        self.session: AsyncSession = session


class BaseDataManager(Generic[T]):
    """
    Base class for managing CRUD operations using SQLAlchemy (sync version).
    """

    def __init__(self, session: Session):
        self.session: Session = session

    def get_one(self, stmt: Select[Any]) -> Optional[T]:
        """Execute a statement and return one record or None."""
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    def get_all(self, stmt: Select[Any]) -> Sequence[T]:
        """Execute a statement and return all records."""
        result = self.session.execute(stmt)
        return result.scalars().all()