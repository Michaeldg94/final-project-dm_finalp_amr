"""Staging (raw) movies table.

Holds the ingested, un-normalized movie records exactly as they arrive
(from CSV). Use this for ETL into the curated `movies` table.
"""

from sqlalchemy.orm import Mapped, mapped_column

from server.models.base import BaseSQLModel


class MoviesRawModel(BaseSQLModel):
    """Raw movie record as ingested (no cleaning or normalization)."""
    __tablename__ = "movies_raw"

    movieId: Mapped[int] = mapped_column(
        primary_key = True
    )  # primary key necessary for sqlalchemy
    title: Mapped[str] = mapped_column()
    genres: Mapped[str] = mapped_column()
