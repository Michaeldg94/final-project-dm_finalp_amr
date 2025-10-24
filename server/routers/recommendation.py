"""Recommendation endpoints.

This router exposes two endpoints:

- POST /api/rest/v1/recommendation-engine
  Trains and versions a recommendation model (NMF) from the latest ratings.

- GET /api/rest/v1/user/{user_id}/recommended-movies?n=10
  Returns the top-N recommended movie IDs and normalized scores for a user.

Both endpoints rely on a PostgreSQL-backed SQLAlchemy Session obtained via
`PostgresSessionManager`, and training metadata/artifacts are logged to MLflow.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Generator
import logging

from server.backend.postgres import PostgresSessionManager
from server.schemas.recommendation import RecommendResponse
from server.services.recommendation import train_and_log_model, recommend_for_user

router = APIRouter(prefix = "/api/rest/v1", tags = ["Recommendation"])
session_manager = PostgresSessionManager()
logger = logging.getLogger(__name__)

def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy :class:`Session` for request-scoped DB access.

    The session is opened from :class:`PostgresSessionManager` and properly
    closed after the request finishes.

    Yields
    ------
    Session
        An active SQLAlchemy session bound to the configured PostgreSQL engine.
    """
    with session_manager.open_session() as session:
        yield session

@router.post("/recommendation-engine", status_code = 204, summary = "Train recommendation model")
def train_recommendation_engine(db: Session = Depends(get_db)) -> None:
    """Train and version the recommendation model using the latest ratings.

    This endpoint:
    - loads rating data from the database,
    - fits a Non-negative Matrix Factorization (NMF) model (with safeguards for
      large/sparse data handled inside the service layer),
    - logs a **new** MLflow run with parameters, metrics, and artifacts 
      (e.g., W/H matrices, user/item mappings).

    On success, returns HTTP 204 (No Content).

    Parameters
    ----------
    db : Session
        A request-scoped SQLAlchemy session injected by FastAPI.

    Raises
    ------
    HTTPException
        500 — if training fails for any reason (details include the exception type).
    """
    try:
        train_and_log_model(db)
    except Exception as e:
        logger.exception("Training failed")
        # include the exception type to speed up debugging from the client side too
        raise HTTPException(status_code = 500, detail = f"{type(e).__name__}: {e}")

@router.get(
    "/user/{user_id}/recommended-movies",
    response_model = RecommendResponse,
    summary = "Get top-N recommendations for a user",
)
def get_recommended_movies(
    user_id: int,
    n: int = Query(10, gt = 0, le = 100, description="Number of movies to return (default 10)"),
) -> RecommendResponse:
    """Return the top-N recommended movies (and normalized scores) for a user.

    The service loads the **latest** trained model (most recent MLflow run).
    If the user is unseen (cold start), a popularity-based fallback is used.

    Parameters
    ----------
    user_id : int
        The ID of the user to generate recommendations for.
    n : int, optional
        Number of items to return (default 10, 1–100).

    Returns
    -------
    RecommendResponse
        Pydantic model with:
        - `movie_ids`: list[int] — movie IDs in descending relevance,
        - `probabilities`: list[float] — normalized scores that sum to 1.

    Raises
    ------
    HTTPException
        500 — if recommendation fails (e.g., no trained model yet).
    """
    try:
        movie_ids, probabilities = recommend_for_user(user_id, n)
        return RecommendResponse(movie_ids = movie_ids, probabilities = probabilities)
    except Exception as e:
        logger.exception("Recommend failed")
        raise HTTPException(status_code = 500, detail = f"{type(e).__name__}: {e}")
