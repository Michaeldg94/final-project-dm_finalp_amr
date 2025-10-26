"""Pydantic schema for Movie entities and responses."""

from typing import List, Optional
from pydantic import Field

from server.schemas.base import BaseSchema
from server.schemas.genres import GenreSchema, GenrePublicSchema


# =======================================
#          MOVIE SCHEMA
# =======================================
class MovieSchema(BaseSchema):
    """Movie with basic fields and its genres (public view)."""
    movie_id: int
    title: str
    genres: List[GenrePublicSchema] = Field(default_factory=list)


# =======================================
#      MOVIE LIST RESPONSE SCHEMA
# =======================================
class MovieListResponse(BaseSchema):
    """Paginated list of movies."""
    movies: List[MovieSchema]
    total: int
    page: int
    limit: int


class MovieResponse(BaseSchema):
    """Single movie response (without relations)."""
    movie_id: int
    title: str


# =======================================
#      AVERAGE RATING RESPONSE SCHEMA
# =======================================
class MovieAvgRatingResponse(BaseSchema):
    """Aggregate rating info for a movie."""
    movie_id: int
    title: str
    avg_rating: Optional[float] = Field(default=None, description="Average rating for this movie")
    total_ratings: int = Field(..., description="Total number of ratings for this movie")
