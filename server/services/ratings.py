"""Ratings service and data access layer.

Provides creation of ratings with validation against users/movies and
the unique (user_id, movie_id) constraint.
"""

from datetime import UTC, datetime

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from server.models.movies import MovieModel
from server.models.ratings import RatingModel
from server.models.user import UserModel
from server.schemas.ratings import RatingCreate, RatingResponse
from server.services.base import BaseDataManager, BaseService


class RatingService(BaseService):
    """Service layer for ratings; returns Pydantic RatingResponse."""

    def create_rating(self, payload: RatingCreate) -> RatingResponse:
        """Validate and create a rating."""
        return RatingDataManager(self.session).create_rating(payload)

    # ↓↓↓ NEW: deletion entrypoint for router ↓↓↓
    def delete_rating(self, user_id: int, movie_id: int) -> None:
        RatingDataManager(self.session).delete_rating(user_id, movie_id)


class RatingDataManager(BaseDataManager):
    """Sync data-access helper for ratings."""

    def __init__(self, session: Session):
        super().__init__(session)

    # ---- helpers ------------------------------------------------------------
    def _ensure_movie_exists(self, movie_id: int) -> None:
        """Raise ValueError if the movie does not exist."""
        stmt = select(MovieModel.movie_id).where(MovieModel.movie_id == movie_id)
        if self.session.execute(stmt).scalar_one_or_none() is None:
            raise ValueError("Movie not found")

    def _ensure_user_exists(self, user_id: int) -> None:
        """Raise ValueError if the user does not exist."""
        stmt = select(UserModel.user_id).where(UserModel.user_id == user_id)
        if self.session.execute(stmt).scalar_one_or_none() is None:
            raise ValueError("User not found")

    def _ensure_not_already_rated(self, user_id: int, movie_id: int) -> None:
        """Raise ValueError if the user already rated the movie."""
        stmt = select(RatingModel.rating_id).where(
            and_(RatingModel.user_id == user_id, RatingModel.movie_id == movie_id)
        )
        if self.session.execute(stmt).scalar_one_or_none() is not None:
            raise ValueError("User already rated this movie")

    # ---- public API ---------------------------------------------------------
    def create_rating(self, payload: RatingCreate) -> RatingResponse:
        # We ensure the given parameters are valid and exists in the database
        self._ensure_movie_exists(payload.movie_id)
        self._ensure_user_exists(payload.user_id)
        self._ensure_not_already_rated(payload.user_id, payload.movie_id)

        model = RatingModel(
            user_id=payload.user_id,
            movie_id=payload.movie_id,
            rating=payload.rating,
            timestamp=datetime.now(UTC),
        )

        self.session.add(model)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            # Covers race vs UNIQUE(user_id, movie_id)
            raise ValueError("User already rated this movie")

        self.session.refresh(model)

        # Build the Pydantic response from ORM attributes (Pydantic v2)
        return RatingResponse.model_validate(model, from_attributes=True)

    # ↓↓↓ deletion method (no timestamp) ↓↓↓
    def delete_rating(self, user_id: int, movie_id: int) -> None:
        """
        Delete a rating by (user_id, movie_id).
        Raises ValueError('Rating not found') if no match.
        """
        stmt = select(RatingModel).where(
            and_(RatingModel.user_id == user_id, RatingModel.movie_id == movie_id)
        )
        obj = self.session.execute(stmt).scalar_one_or_none()
        if obj is None:
            raise ValueError("Rating not found")

        self.session.delete(obj)
        self.session.commit()
