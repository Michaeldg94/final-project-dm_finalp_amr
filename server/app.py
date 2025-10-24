"""FastAPI application entrypoint."""

from fastapi import FastAPI
from .routers import movie, ratings, recommendation
from typing import Dict


app = FastAPI(
    title = "Movies & Ratings API",
    description = "Simple API exposing movies, genres, and user ratings.",
)


@app.get("/", summary="Health check", tags=["Meta"])
def read_root() -> Dict[str, str]:
    """Basic health endpoint to verify the API is running."""
    return {"message": "Hello FastAPI"}


# @app.get("/items/{item_id}", summary = "Echo an item id", tags = ["Meta"])
# def read_item(item_id: int) -> Dict[str, int]:
#     """Return the provided `item_id` for quick testing."""
#     return {"item_id": item_id}

# Routers
app.include_router(movie.router)
app.include_router(ratings.router)
app.include_router(recommendation.router) 