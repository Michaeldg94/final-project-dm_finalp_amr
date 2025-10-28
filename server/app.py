from fastapi import FastAPI
from .routers import movie, ratings, recommendation

app = FastAPI(
    title = "Movies & Ratings API",
    description = "Simple API exposing movies, genres, and user ratings.",
)

# Routers
app.include_router(movie.router)
app.include_router(ratings.router)
app.include_router(recommendation.router) 