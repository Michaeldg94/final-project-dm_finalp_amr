from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from server.backend.postgres import PostgresSessionManager
from server.models import MovieModel
from server.schemas.movie import MovieResponse

router = APIRouter(prefix="/movies", tags=["Movies"])

session_manager = PostgresSessionManager()


# 🔹 Dependencia para inyectar la sesión en las rutas
def get_db() -> Generator[Session, None, None]:
    with session_manager.open_session() as session:
        yield session


@router.get("/{movie_id}", response_model=MovieResponse)
async def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(MovieModel).filter(MovieModel.movie_id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )
    return movie


"""
DOES NOT WORK
@router.get("/{movie_id}", response_model=MovieModel)
async def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(MovieModel).filter(MovieModel.movie_id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hiiiiiiiiii")
    return movie
"""

"""
@router.get("/{movie_id}", response_model=MovieAvgRatingResponse)
async def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with id {movie_id} not found",
        )
    return movie
"""

'''
@router.get("/{movie_id}/avg-rating", response_model=MovieAvgRatingResponse)
async def movie_avg_rating(
    movie_id: int,
    db: Annotated[Session, Depends(get_db)] = Depends(),
) -> MovieAvgRatingResponse:
    row = svc.avg_rating(movie_id)
    if not row:
        raise HTTPException(status_code=404, detail="movie_not_found")
    return {
        "movie_id": row.movie_id,
        "title": row.title,
        "avg_rating": round(float(row.avg_rating), 3)
        if row.avg_rating is not None
        else 0.0,
        "total_ratings": int(row.total_ratings),
    }

    """offset = (page - 1) * limit

    # Base query
    query = select(MovieModel).distinct().join(MovieModel.genres, isouter=True)

    # Apply search if provided
    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(
            func.lower(MovieModel.title).like(search_term)
            | func.lower(GenreModel.genre_name).like(search_term)
        )

    # Count total results
    total_query = select(func.count(func.distinct(MovieModel.movie_id))).select_from(
        MovieModel
    ).join(MovieModel.genres, isouter=True)

    if search:
        total_query = total_query.where(
            func.lower(MovieModel.title).like(search_term)
            | func.lower(GenreModel.genre_name).like(search_term)
        )

    total = (await session.execute(total_query)).scalar_one()

    # Fetch paginated results
    query = query.offset(offset).limit(limit)
    result = await session.execute(query)
    movies = result.scalars().unique().all()
"""
'''
