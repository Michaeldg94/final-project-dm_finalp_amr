
from typing import List

from sqlalchemy import select, func

from server.models.movies import MovieModel
from server.models.ratings import RatingModel
from server.schemas.movie import MovieSchema
from server.services.base import BaseDataManager, BaseService


class MovieService(BaseService):
    def get_movie(self, movie_id: int) -> MovieSchema:
        return MovieDataManager(self.session).get_movie(movie_id)

    def get_movies(self, year: int, rating: float) -> List[MovieSchema]:
        return MovieDataManager(self.session).get_movies(year, rating)
    
    def get_movies_paginated(self, page: int, page_size: int = 10) -> List[MovieSchema]:
        """Return a paginated list of movies."""
        return MovieDataManager(self.session).get_movies_paginated(page, page_size)
    
    def get_avg_rating(self, movie_id: int):
        return MovieDataManager(self.session).avg_rating(movie_id)

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
    
    
    def get_movies_paginated(self, page: int, page_size: int = 10) -> List[MovieSchema]:
        """Return a list of movies for a given page."""
        offset = (page - 1) * page_size
        stmt = (
        select(MovieModel)
        .order_by(MovieModel.movie_id)  # ✅ ensures consistent order
        .offset(offset)
        .limit(page_size)
    )
        models = self.get_all(stmt)
        return [MovieSchema(**m.to_dict()) for m in models]
