
"""Movie service and data access layer.

Exposes high-level methods for fetching movies, paginating/searching,
and computing aggregate rating stats. Uses SQLAlchemy (sync).
"""

from typing import List, Optional, Tuple

from sqlalchemy import select, func, or_, case
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects import postgresql

from server.models.movies import MovieModel
from server.models.ratings import RatingModel
from server.models.genres import GenreModel
from server.schemas.movie import MovieSchema
from server.services.base import BaseDataManager, BaseService

# ======================================
#           SERVICE LAYER
# ======================================
class MovieService(BaseService):
    """Application-facing operations for movies."""
    
    def get_movies_paginated(
        self, page: int, limit: int, search: Optional[str] = None
    ) -> Tuple[List[MovieSchema], int]:
        
        """Return a page of movies (as schemas) plus the total count.

        Args:
            page: 1-based page index.
            limit: max items per page.
            search: optional case-insensitive filter on title or genre.

        Returns:
            (schemas, total) where `schemas` is the list of `MovieSchema` and
            `total` is the total number of matching movies.
        """
        
        models, total = MovieDataManager(self.session).get_movies_paginated(
            page=page, limit=limit, search=search
        )
        # Convert ORM models to Pydantic schemas
        schemas = [MovieSchema.model_validate(m) for m in models]
        return schemas, total
    
    def get_avg_rating(self, movie_id: int):
        """Return title, avg_rating, and total_ratings for a movie (or None)."""
        return MovieDataManager(self.session).avg_rating(movie_id)


# ======================================
#           DATA ACCESS LAYER
# ======================================

class MovieDataManager(BaseDataManager):
    """SQLAlchemy queries for movie data."""
    def get_movie(self, movie_id: int) -> MovieSchema:
        """Fetch a single movie and map it to `MovieSchema`."""
        stmt = select(MovieModel).where(MovieModel.movie_id == movie_id)
        model = self.get_one(stmt)

        return MovieSchema(**model.to_dict())

    def get_movies(self, year: int, rating: float) -> List[MovieSchema]:
        """Fetch movies by year and minimum rating (example filter)."""
        schemas: List[MovieSchema] = list()

        stmt = select(MovieModel).where(
            MovieModel.released >= year,
            MovieModel.rating >= rating,
        )

        for model in self.get_all(stmt):
            schemas += [MovieSchema(**model.to_dict())]

        return schemas
    
    def get_movies_paginated(
        self,
        page: int = 1,
        limit: int = 10,
        search: Optional[str] = None,
    ) -> Tuple[List[MovieModel], int]:
        """Return paginated movies matching title or genre, ordered by relevance."""
        offset = (page - 1) * limit

        if not search:
            total = self.session.query(func.count(MovieModel.movie_id)).scalar()
            movies = (
                self.session.query(MovieModel)
                .options(selectinload(MovieModel.genres))
                .order_by(MovieModel.title.asc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return movies, total

        search_lower = search.lower()
        search_term = f"%{search_lower}%"

        # Subquery: find matching movie_ids + relevance
        relevance_expr = (
            case((func.lower(MovieModel.title) == search_lower, 3), else_=0)
            + case((func.lower(MovieModel.title).like(search_term), 2), else_=0)
            + case((func.lower(GenreModel.genre_name).like(search_term), 1), else_=0)
        ).label("relevance")

        subq = (
            select(MovieModel.movie_id, relevance_expr)
            .join(MovieModel.genres, isouter=True)
            .where(
                or_(
                    func.lower(MovieModel.title).like(search_term),
                    func.lower(GenreModel.genre_name).like(search_term),
                )
            )
            .distinct()
            .subquery()
        )

        # Count how many unique movie_ids matched
        count_stmt = select(func.count()).select_from(subq)
        total = self.session.execute(count_stmt).scalar() or 0

        # Outer query: join back on movie_id and order by relevance
        query = (
            self.session.query(MovieModel)
            .join(subq, subq.c.movie_id == MovieModel.movie_id)
            .options(selectinload(MovieModel.genres))
            .order_by(subq.c.relevance.desc(), MovieModel.title.asc())
            .offset(offset)
            .limit(limit)
        )

        movies = query.all()
        return movies, total
    
    def avg_rating(self, movie_id: int):
        """Return movie title, avg_rating, and total_ratings for a movie."""
        stmt = (
            select(
                MovieModel.movie_id,
                MovieModel.title,
                func.avg(RatingModel.rating).label("avg_rating"),
                func.count(RatingModel.rating_id).label("total_ratings"),
            )
            .join(RatingModel, MovieModel.movie_id == RatingModel.movie_id, isouter=True)
            .where(MovieModel.movie_id == movie_id)
            .group_by(MovieModel.movie_id)
        )

        result = self.session.execute(stmt).first()
        return result  # will be a Row with (movie_id, title, avg_rating, total_ratings)
    
    