from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_


from server.backend.postgres import PostgresSessionManager
from server.models import MovieModel, GenreModel
from server.schemas.movie import MovieResponse, MovieListResponse, MovieAvgRatingResponse
from server.services.movie import MovieService


router = APIRouter(prefix="/api/rest/v1/movies", tags=["Movies"])

session_manager = PostgresSessionManager()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy `Session`."""
    with session_manager.open_session() as session:
        yield session

@router.get("/", response_model=MovieListResponse)
async def get_movie_list(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    service = MovieService(db)
    movies, total = service.get_movies_paginated(page=page, limit=limit, search=search)

    if not movies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No movies found for this page.",
        )

    return MovieListResponse(
        movies=movies,
        page=page,
        limit=limit,
        total=total,
    )
    
@router.get("/{movie_id}/avg-rating", response_model=MovieAvgRatingResponse)
async def get_movie_avg_rating(movie_id: int, db: Session = Depends(get_db)):
    service = MovieService(db)
    row = service.get_avg_rating(movie_id)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with id {movie_id} not found or has no ratings."
        )

    # row is a SQLAlchemy Row object
    avg_rating = float(row.avg_rating) if row.avg_rating is not None else None
    total_ratings = int(row.total_ratings) if row.total_ratings is not None else 0

    return MovieAvgRatingResponse(
    movie_id=row.movie_id,
    title=row.title,
    avg_rating=avg_rating,
    total_ratings=total_ratings,
    )

