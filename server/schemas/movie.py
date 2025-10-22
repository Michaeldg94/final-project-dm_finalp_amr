from typing import List

from pydantic import BaseModel, Field

from server.schemas.genres import GenreSchema, GenrePublicSchema


# =======================================
#          MOVIE SCHEMA
# =======================================
class MovieSchema(BaseModel):
    movie_id: int
    title: str
    genres: List[GenrePublicSchema] = []

    class Config:
        from_attributes = True 

# =======================================
#      MOVIE LIST RESPONSE SCHEMA
# =======================================
class MovieListResponse(BaseModel):
    movies: List[MovieSchema]
    total: int
    page: int
    limit: int
    
   
    
    class Config:
        from_attributes = True 



class MovieResponse(BaseModel):
    movie_id: int
    title: str

    class Config:
        orm_mode = True



# =======================================
#      AVERAGE RATING RESPONSE SCHEMA
# =======================================
class MovieAvgRatingResponse(BaseModel):
    movie_id: int
    title: str
    avg_rating: float = Field(..., description="Average rating for this movie")
    total_ratings: int = Field(
        ..., description="Total number of ratings for this movie"
    )
    class Config:
        from_attributes = True 