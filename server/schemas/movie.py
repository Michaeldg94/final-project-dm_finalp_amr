"""Pydantic schema for Movie entities and responses."""

from typing import List, Optional

from pydantic import BaseModel, Field

from server.schemas.genres import GenreSchema, GenrePublicSchema


# =======================================
#          MOVIE SCHEMA
# =======================================
class MovieSchema(BaseModel):
    """Movie with basic fields and its genres (public view)."""
    movie_id: int
    title: str
    genres: List[GenrePublicSchema] = []

    class Config:
        from_attributes = True 

# =======================================
#      MOVIE LIST RESPONSE SCHEMA
# =======================================
class MovieListResponse(BaseModel):
    """Paginated list of movies."""
    movies: List[MovieSchema]
    total: int
    page: int
    limit: int
    
   
    
    class Config:
        from_attributes = True 



class MovieResponse(BaseModel):
    """Single movie response (without relations)."""
    movie_id: int
    title: str

    class Config:
        orm_mode = True



# =======================================
#      AVERAGE RATING RESPONSE SCHEMA
# =======================================
class MovieAvgRatingResponse(BaseModel):
    """Aggregate rating info for a movie."""
    movie_id: int
    title: str
    avg_rating: Optional[float] = Field(default = None, description="Average rating for this movie")
    total_ratings: int = Field(
        ..., description = "Total number of ratings for this movie"
    )
    class Config:
        from_attributes = True 