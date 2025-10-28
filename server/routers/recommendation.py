"""Recommendation endpoints.

This router exposes three endpoints:

- POST /api/rest/v1/recommendation-engine
  Now **non-blocking**: enqueues training as a FastAPI BackgroundTask and
  returns 202 {task_id, status:"queued"} immediately.

- GET  /api/rest/v1/recommendation-engine/{task_id}
  Poll job status and (if desired) any future training result/metadata.

- GET  /api/rest/v1/user/{user_id}/recommended-movies?n=10
  Returns the top-N recommended movie IDs and normalized scores for a user.

Notes
-----
- The background job **opens its own DB session** using PostgresSessionManager.
  Do not pass the request-scoped session into background tasks.
- For production, consider persisting the task store (Redis/DB). Here we use
  a simple in-memory dict for clarity.
"""

from __future__ import annotations

import logging
from typing import Callable, Generator, List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from server.backend.postgres import PostgresSessionManager
from server.schemas.recommendation import RecommendResponse
from server.services.recommendation import recommend_for_user, train_and_log_model

router = APIRouter(prefix="/api/rest/v1", tags=["Recommendation"])
session_manager = PostgresSessionManager()
logger = logging.getLogger(__name__)


# ───────────────────────────── Dependencies ─────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy `Session`."""
    with session_manager.open_session() as session:
        yield session


def get_trainer() -> Callable[[Session], str]:
    """Provide the training function (DI). Patches easily in tests."""
    return train_and_log_model


def get_session_manager() -> PostgresSessionManager:
    """Provide the session manager (DI)."""
    return session_manager


# ───────────────────────────── Task store (in-memory) ─────────────────────────────

class _TaskStore:
    """Ultra-light in-memory task store.

    Status values: "queued" | "running" | "done" | "error" | "not_found"
    """
    _data: dict[str, dict] = {}

    @classmethod
    def create(cls, task_id: str) -> None:
        cls._data[task_id] = {"status": "queued", "run_id": None, "error": None}

    @classmethod
    def set_running(cls, task_id: str) -> None:
        cls._data[task_id]["status"] = "running"

    @classmethod
    def set_done(cls, task_id: str, run_id: str | None) -> None:
        cls._data[task_id]["status"] = "done"
        cls._data[task_id]["run_id"] = run_id

    @classmethod
    def set_error(cls, task_id: str, msg: str) -> None:
        cls._data[task_id]["status"] = "error"
        cls._data[task_id]["error"] = msg

    @classmethod
    def get(cls, task_id: str) -> dict:
        item = cls._data.get(task_id)
        if not item:
            return {"task_id": task_id, "status": "not_found"}
        return {"task_id": task_id, **item}


# ───────────────────────────── Schemas for background job ─────────────────────────────

class SubmitResponse(BaseModel):
    """Response returned by POST /recommendation-engine."""
    task_id: str = Field(..., description="Identifier for the training job.")
    status: str = Field(..., description="Initial status, usually 'queued'.")


class TaskResult(BaseModel):
    """Status returned by GET /recommendation-engine/{task_id}."""
    task_id: str
    status: str  # queued|running|done|error|not_found
    run_id: Optional[str] = Field(None, description="MLflow run id (if any).")
    error: Optional[str] = Field(None, description="Error message if status=='error'.")


# ───────────────────────────── Background worker ─────────────────────────────

async def _run_training_task(
    task_id: str,
    sm: PostgresSessionManager,
    trainer: Callable[[Session], str],
) -> None:
    """Execute training in the background.

    Opens a **fresh** DB session (do not reuse the request-scoped one),
    runs the training function, and records status in the task store.
    """
    try:
        _TaskStore.set_running(task_id)
        with sm.open_session() as db:
            run_id = trainer(db)
        _TaskStore.set_done(task_id, run_id)
    except Exception as exc:  # noqa: BLE001 — we want to record all failures
        logger.exception("Training failed (task_id=%s)", task_id)
        _TaskStore.set_error(task_id, f"{type(exc).__name__}: {exc}")


# ───────────────────────────── Routes ─────────────────────────────

@router.post(
    "/recommendation-engine",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=SubmitResponse,
    summary="Enqueue training of the recommendation model",
)
async def train_recommendation_engine_async(
    background: BackgroundTasks,
    trainer: Callable[[Session], str] = Depends(get_trainer),
    sm: PostgresSessionManager = Depends(get_session_manager),
) -> SubmitResponse:
    """Enqueue the training job and return immediately.

    Returns 202 Accepted with a `task_id`. Clients should then poll
    GET /api/rest/v1/recommendation-engine/{task_id} to track status.
    """
    task_id = str(uuid4())
    _TaskStore.create(task_id)
    background.add_task(_run_training_task, task_id, sm, trainer)
    return SubmitResponse(task_id=task_id, status="queued")


@router.get(
    "/recommendation-engine/{task_id}",
    response_model=TaskResult,
    summary="Poll training job status",
)
async def get_training_status(task_id: str) -> TaskResult:
    """Return the current status of a training job."""
    return TaskResult.model_validate(_TaskStore.get(task_id))


@router.get(
    "/user/{user_id}/recommended-movies",
    response_model=RecommendResponse,
    summary="Get top-N recommendations for a user",
)
def get_recommended_movies(
    user_id: int,
    n: int = Query(10, gt=0, le=100, description="Number of movies to return (default 10)"),
) -> RecommendResponse:
    """Return the top-N recommended movies (and normalized scores) for a user.

    The service loads the **latest** trained model (most recent MLflow run).
    If the user is unseen (cold start), a popularity-based fallback is used.
    """
    try:
        movie_ids, probabilities = recommend_for_user(user_id, n)
        return RecommendResponse(movie_ids=movie_ids, probabilities=probabilities)
    except Exception as e:
        logger.exception("Recommend failed")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
