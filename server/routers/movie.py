from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from server.schemas.movie import MovieListResponse
from server.schemas.ratings import MovieAvgRatingResponse
from server.services import movie as svc

router = APIRouter(prefix="/movies", tags=["Movies"])


@router.get("", response_model=MovieListResponse)
async def list_movies(
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    page: Annotated[int, Query(ge=1)] = 1,
    search: Annotated[
        str | None, Query(description="Full-text search in title and genres")
    ] = None,
) -> MovieListResponse:
    items, total = svc.search_movies(db, limit=limit, page=page, search=search)
    return {"movies": items, "total": total, "page": page, "limit": limit}


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
