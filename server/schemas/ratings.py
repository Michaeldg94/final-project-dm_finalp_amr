from pydantic import BaseModel, Field


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
