
from typing import List, Optional, Tuple

from sqlalchemy import select, func, or_, case
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
    def get_movie(self, movie_id: int) -> MovieSchema:
        return MovieDataManager(self.session).get_movie(movie_id)

    def get_movies(self, year: int, rating: float) -> List[MovieSchema]:
        return MovieDataManager(self.session).get_movies(year, rating)
    
    def get_movies_paginated(
        self, page: int, limit: int, search: Optional[str] = None
    ) -> Tuple[List[MovieSchema], int]:
        
        """Return paginated MovieSchema list and total count."""
        
        models, total = MovieDataManager(self.session).get_movies_paginated(
            page=page, limit=limit, search=search
        )
        # Convert ORM models to Pydantic schemas
        schemas = [MovieSchema.model_validate(m) for m in models]
        return schemas, total
    
    def get_avg_rating(self, movie_id: int):
        return MovieDataManager(self.session).avg_rating(movie_id)


# ======================================
#           DATA ACCESS LAYER
# ======================================

class MovieDataManager(BaseDataManager):
    def get_movie(self, movie_id: int) -> MovieSchema:
        stmt = select(MovieModel).where(MovieModel.movie_id == movie_id)
        model = self.get_one(stmt)

        return MovieSchema(**model.to_dict())

    def get_movies(self, year: int, rating: float) -> List[MovieSchema]:
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
        """Return a list of MovieModel instances and total count."""
        offset = (page - 1) * limit

        # Base query
        stmt = select(MovieModel).join(MovieModel.genres, isouter=True)

        # Apply search filter
        if search:
            search_lower = search.lower()
            search_term = f"%{search_lower}%"

            # WHERE filters (match title or genre)
            stmt = stmt.where(
                or_(
                    func.lower(MovieModel.title).like(search_term),
                    func.lower(GenreModel.genre_name).like(search_term),
                )
            )

            # ORDER BY relevance (title exact > title partial > genre match)
            stmt = stmt.order_by(
                case((func.lower(MovieModel.title) == search_lower, 3), else_=0).desc(),
                case((func.lower(MovieModel.title).like(search_term), 2), else_=0).desc(),
                case((func.lower(GenreModel.genre_name).like(search_term), 1), else_=0).desc(),
                MovieModel.title.asc(),
            )

        else:
            # Default ordering if no search term
            stmt = stmt.order_by(MovieModel.title.asc())

        print("\n=== DEBUG SQL ===")
        print(
            stmt.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True}
            ),
            flush=True
        )
        print("=================\n")
        # Count total
        count_stmt = (
            select(func.count(func.distinct(MovieModel.movie_id)))
            .select_from(MovieModel)
            .join(MovieModel.genres, isouter=True)
        )

        if search:
            count_stmt = count_stmt.where(
                or_(
                    func.lower(MovieModel.title).like(search_term),
                    func.lower(GenreModel.genre_name).like(search_term),
                )
            )

        total = self.session.execute(count_stmt).scalar() or 0

        # Fetch paginated results
        stmt = stmt.offset(offset).limit(limit)

        models = self.get_all(stmt)

        return models, total
   
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
    
    