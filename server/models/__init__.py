"""Convenience imports for ORM models.

This module re-exports the most commonly used SQLAlchemy models so you
can write clean imports like:

    from server.models import UserModel, MovieModel

instead of importing from each submodule.
"""


from server.models.genres import GenreModel
from server.models.movies import MovieModel
from server.models.movies_genres import MovieGenreModel
from server.models.movies_raw import MoviesRawModel
from server.models.ratings import RatingModel
from server.models.ratings_raw import RatingsRawModel
from server.models.user import UserModel

__all__ = [
    "UserModel",
    "MovieModel",
    "GenreModel",
    "MovieGenreModel",
    "MoviesRawModel",
    "RatingsRawModel",
    "RatingModel",
]
