"""Base Pydantic schema.

All response/request schemas should inherit from `BaseSchema`
to enable `from_attributes=True` (ORM mode) for SQLAlchemy models.
"""

from pydantic import BaseModel, ConfigDict

class BaseSchema(BaseModel):
    """Common Pydantic config for project schemas.

    Enables population from SQLAlchemy ORM objects without manual dict conversion.
    """
    model_config = ConfigDict(from_attributes=True)
