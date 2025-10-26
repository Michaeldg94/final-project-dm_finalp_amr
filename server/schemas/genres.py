"""Pydantic schemas for Genre entities."""

from pydantic import Field, ConfigDict

from server.schemas.base import BaseSchema

class GenreSchema(BaseSchema):
    """Public-facing genre with id and name."""
    id: int = Field(alias="genre_id", description="Genre identifier")
    genre_name: str = Field(description="Genre name")

    # Optional: accept either field name ("id") or alias ("genre_id") as input
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class GenrePublicSchema(BaseSchema):
    """Payload for creating/updating a genre."""
    genre_name: str = Field(description="Genre name")
