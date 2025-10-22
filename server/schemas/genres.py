from pydantic import BaseModel

class GenreSchema(BaseModel):
    id: int
    genre_name: str
    class Config:
        from_attributes = True

class GenrePublicSchema(BaseModel):
    genre_name: str  
    class Config:
        from_attributes = True