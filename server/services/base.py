from typing import Any, Generic, Optional, Sequence, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
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
    Clase base genérica para manejar operaciones CRUD
    sobre modelos SQLAlchemy, con tipado compatible con Pylance.
    """

    def __init__(self, session: AsyncSession):
        self.session: AsyncSession = session

    async def get_one(self, stmt: Select[Any]) -> Optional[T]:
        """
        Ejecuta un statement y devuelve un único registro o None.
        """
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, stmt: Select[Any]) -> Sequence[T]:
        """
        Ejecuta un statement y devuelve una lista de registros.
        """
        result = await self.session.execute(stmt)
        return result.scalars().all()
