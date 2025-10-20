from typing import List

from pydantic import BaseModel

from server.schemas.genres import GenreSchema


# =======================================
#          MOVIE SCHEMA
# =======================================
class MovieSchema(BaseModel):
    movie_id: int
    title: str
    genres: List[GenreSchema] = []

    class Config:
        orm_mode = True


# =======================================
#      MOVIE LIST RESPONSE SCHEMA
# =======================================
class MovieListResponse(BaseModel):
    movies: List[MovieSchema]
    total: int
    page: int
    limit: int
