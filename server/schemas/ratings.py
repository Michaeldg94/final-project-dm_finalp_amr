"""Pydantic schemas for creating and returning ratings."""

from datetime import datetime
from pydantic import Field

from server.schemas.base import BaseSchema

# This schema is used for instantiating an object that the user wants to post
class RatingCreate(BaseSchema):
    """Payload for creating a new rating."""
    user_id: int
    movie_id: int
    rating: float = Field(..., ge=0.5, le=5.0, description="Rating value (0.5–5.0)")

# This schema structures the response returned by the endpoint
class RatingResponse(BaseSchema):
    """Response model for a rating record."""
    rating_id: int
    user_id: int
    movie_id: int
    rating: float = Field(..., ge=0.5, le=5.0, description="Rating value (0.5–5.0).")
    timestamp: datetime = Field(..., description="When the rating was created (ISO 8601).")
