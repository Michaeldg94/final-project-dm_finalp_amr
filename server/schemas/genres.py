from pydantic import BaseModel


# =======================================
#          GENRE SCHEMA
# =======================================
class GenreSchema(BaseModel):
    genre_id: int
    genre_name: str

    class Config:
        orm_mode = True
