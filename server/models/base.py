"""Base class for all SQLAlchemy ORM models.

All models in the project should inherit from `BaseSQLModel`
to ensure consistent metadata and declarative mapping behavior.
"""

from sqlalchemy.orm import DeclarativeBase


class BaseSQLModel(DeclarativeBase):
    pass
