from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_


from server.backend.postgres import PostgresSessionManager
from server.models import MovieModel, GenreModel
from server.schemas.movie import MovieResponse, MovieListResponse, MovieAvgRatingResponse
from server.services.movie import MovieService


router = APIRouter(prefix="/api/rest/v1/movies", tags=["Movies"])

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

@router.get("/", response_model=MovieListResponse)
async def get_movie_list(page: int = Query(1, ge=1, description="Page number (starts at 1)"),
                        limit: int = Query(10, ge=1, le=100, description="Number of movies per page"),
                        search: str | None = Query(None, description="Search in title or genre name"),
                        db: Session = Depends(get_db)):
    offset = (page - 1) * limit
    
    query = db.query(MovieModel)

    
    if search:
        search_term = f"%{search.lower()}%"
        query = (
            query.join(MovieModel.genres)
            .filter(
                or_(
                func.lower(MovieModel.title).like(search_term),
                func.lower(GenreModel.genre_name)==search_term
            ))
            .distinct()
        )

    total = query.count()
    movies = query.offset(offset).limit(limit).all()

   

    if not movies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No movies found for this page."
        )
    return MovieListResponse(
        movies=movies,
        page=page,
        limit=limit,
        total=total,
    )

@router.get("/{movie_id}/avg-rating", response_model=MovieAvgRatingResponse)
async def get_movie_avg_rating(movie_id: int, db: Session = Depends(get_db)):
    service = MovieService(db)
    row = service.get_avg_rating(movie_id)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with id {movie_id} not found or has no ratings."
        )

    # row is a SQLAlchemy Row object
    avg_rating = float(row.avg_rating) if row.avg_rating is not None else None
    total_ratings = int(row.total_ratings) if row.total_ratings is not None else 0

    return MovieAvgRatingResponse(
    movie_id=row.movie_id,
    title=row.title,
    avg_rating=avg_rating,
    total_ratings=total_ratings,
    )

"""
DOES NOT WORK        "total": total,

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
