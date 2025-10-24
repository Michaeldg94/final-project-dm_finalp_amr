"""Staging (raw) ratings table.

Holds ratings exactly as ingested from the source (CSV),
before any cleaning or deduplication.
"""

from sqlalchemy import Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from server.models.base import BaseSQLModel


class RatingsRawModel(BaseSQLModel):
    """Raw user - movie rating as ingested (no normalization)."""

    __tablename__ = "ratings_raw"

    userId: Mapped[int] = mapped_column(
        Integer, primary_key = True
    )  # primary key necessary for sqlalchemy
    movieId: Mapped[int] = mapped_column(
        Integer, primary_key = True
    )  # primary key necessary for sqlalchemy
    rating: Mapped[float] = mapped_column(Numeric(2, 1))
    timestamp: Mapped[int] = mapped_column(Integer)
