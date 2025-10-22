# =======================================
#          RATING RESPONSE SCHEMA
# =======================================
from datetime import datetime
from pydantic import BaseModel, Field

#This schema is used for instanting an object that the user wants to post
class RatingCreate(BaseModel):
    user_id: int
    movie_id: int
    rating: float = Field(..., ge=0.5, le=5.0, description="Rating value (0.5–5.0)")

    class Config:
        from_attributes = True
        
#This schema is used for structuring the kind of response that we are getting from the endpoint
class RatingResponse(BaseModel):
    rating_id: int
    user_id: int
    movie_id: int
    rating: float = Field(
        ...,
        ge=0.5,
        le=5.0,
        description="Rating value (0.5–5.0)."
    )
    timestamp: datetime = Field(
        ...,
        description="When the rating was created (ISO 8601)."
    )

    class Config:
        from_attributes = True