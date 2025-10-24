"""Pydantic schemas for Genre entities."""

from pydantic import BaseModel, Field, ConfigDict

class GenreSchema(BaseModel):
    """Public-facing genre with id and name."""
    id: int = Field(alias = "genre_id", description = "Genre identifier")
    genre_name: str = Field(description = "Genre name")
    class Config:
        from_attributes = True

class GenrePublicSchema(BaseModel):
    """Payload for creating/updating a genre."""
    genre_name: str = Field(description = "Genre name")
    class Config:
        from_attributes = True