"""Router-level tests for the Ratings API.

These tests verify the behavior of the /api/rest/v1/ratings endpoints.
They never touch a real database and instead:
- Override the router’s `get_db` dependency with a fake session.
- Monkeypatch the router’s imported `RatingService` to return
  deterministic responses or raise controlled exceptions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.routers import ratings as ratings_router_mod
from server.schemas.ratings import RatingResponse

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


# ─────────────────────────── Fixtures & setup ────────────────────────────────

class _NeutralSession:
    """Minimal fake DB session used to satisfy the `get_db` dependency.

    The router under test constructs a service with this session, but because we
    patch the service class itself, the fake session is never actually used.
    """
    pass


@pytest.fixture()
def app() -> FastAPI:
    """Create a FastAPI app with only the Ratings router and a fake DB dependency."""
    app = FastAPI()
    app.include_router(ratings_router_mod.router)
    app.dependency_overrides[ratings_router_mod.get_db] = lambda: _NeutralSession()
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    """Return a TestClient bound to the minimal test app."""
    return TestClient(app)


# ─────────────────────────── Tests: POST / (create) ───────────────────────────

def test_create_rating_201(client: TestClient, monkeypatch: "MonkeyPatch") -> None:
    """POST /api/rest/v1/ratings/ → 201 and a valid RatingResponse on success."""
    class FakeRatingService:
        def __init__(self, _db: object) -> None:
            # The route still passes a DB session, but we won't use it.
            pass

        def create_rating(self, payload: object) -> RatingResponse:
            # Build a valid response using the incoming JSON payload fields.
            data = payload if isinstance(payload, dict) else payload.__dict__
            return RatingResponse(
                rating_id=123,
                user_id=int(data["user_id"]),
                movie_id=int(data["movie_id"]),
                rating=float(data["rating"]),
                timestamp=datetime.now(UTC),
            )

    # Patch the symbol as imported in the router module.
    monkeypatch.setattr(ratings_router_mod, "RatingService", FakeRatingService)

    resp = client.post(
        "/api/rest/v1/ratings/",
        json={"user_id": 1, "movie_id": 2, "rating": 4.5},
    )
    assert resp.status_code == 201, resp.text

    # Validate response schema/shape via Pydantic
    body = RatingResponse.model_validate(resp.json())
    assert body.rating_id == 123
    assert body.user_id == 1
    assert body.movie_id == 2
    assert body.rating == 4.5
    assert body.timestamp.tzinfo is not None


# ──────────────────────── Tests: error mapping behavior ───────────────────────

@pytest.mark.parametrize(
    ("msg", "status"),
    [
        ("Movie not found", 404),
        ("User not found", 404),
        ("User already rated this movie", 409),
        ("Some other validation", 400),
    ],
)
def test_create_rating_error_mapping(
    client: TestClient,
    monkeypatch: "MonkeyPatch",
    msg: str,
    status: int,
) -> None:
    """Router maps `ValueError` messages from the service to correct HTTP status."""
    class FakeRatingService:
        def __init__(self, _db: object) -> None:
            pass

        def create_rating(self, _payload: object) -> RatingResponse:
            raise ValueError(msg)

    monkeypatch.setattr(ratings_router_mod, "RatingService", FakeRatingService)

    resp = client.post(
        "/api/rest/v1/ratings/",
        json={"user_id": 1, "movie_id": 2, "rating": 4.0},
    )
    assert resp.status_code == status
    assert msg in resp.json()["detail"]
