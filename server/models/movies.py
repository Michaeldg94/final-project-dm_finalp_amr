"""Curated movie entity and its relationships."""

from typing import TYPE_CHECKING

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import BaseSQLModel

if TYPE_CHECKING:
    from server.models.genres import GenreModel
    from server.models.ratings import RatingModel

else:
    GenreModel = "GenreModel"
    RatingModel = "RatingModel"


class MovieModel(BaseSQLModel):
    """A canonical movie record (cleaned/normalized).

    Attributes:
        movie_id: Surrogate primary key.
        title: title (normalized).
        ratings: One-to-many relation to user ratings.
        genres: Many-to-many relation via `movie_genres`.
    """
    __tablename__ = "movies"

    movie_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    ratings: Mapped[list[RatingModel]] = relationship(
        back_populates = "movie", cascade = "all, delete-orphan"
    )
    genres: Mapped[list[GenreModel]] = relationship(
        back_populates = "movies", secondary = "movie_genres"
    )
