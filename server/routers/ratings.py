"""Ratings API endpoints.

Provides:
- POST /: Create a new rating for a movie by a user.
"""

from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from server.backend.postgres import PostgresSessionManager
from server.schemas.ratings import RatingCreate, RatingDelete, RatingResponse
from server.services.ratings import RatingService

router = APIRouter(prefix="/api/rest/v1/ratings", tags=["Ratings"])
session_manager = PostgresSessionManager()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy `Session`."""
    with session_manager.open_session() as session:
        yield session


@router.post("/", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
async def create_rating(
    payload: RatingCreate, db: Session = Depends(get_db)
) -> RatingResponse:
    """Create a new rating.

    Body:
        `{"user_id": 1, "movie_id": 1, "rating": 2.0}`

    Returns:
        The created rating resource.

    Raises:
        404: If the movie or user does not exist.
        409: If the user has already rated this movie.
        400: For other validation errors.
    """
    service = RatingService(db)
    try:
        return service.create_rating(payload)
    except ValueError as e:
        msg = str(e)
        if msg in {"Movie not found", "User not found"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if msg == "User already rated this movie":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.delete(
    "/{user_id}/{movie_id}",
    response_model=RatingDelete,  # returns a confirmation payload
    status_code=status.HTTP_200_OK,  # 200 so we can include a body
    summary="Delete a rating by user_id, movie_id",
)
def delete_rating(
    user_id: int,
    movie_id: int,
    db: Session = Depends(get_db),
) -> RatingDelete:
    """
    Delete a rating.

    Path params:
        user_id: int
        movie_id: int

    Returns:
        200 OK with a confirmation message on success.

    Raises:
        404: If the rating does not exist.
        400: For other validation errors.
    """
    service = RatingService(db)
    try:
        service.delete_rating(user_id=user_id, movie_id=movie_id)  # <-- no timestamp
    except ValueError as e:
        msg = str(e)
        if msg == "Rating not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return RatingDelete(
        user_id=user_id,
        movie_id=movie_id,
        message=f"Deletion completed for user_id={user_id} and movie_id={movie_id}.",
    )
