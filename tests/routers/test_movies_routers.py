"""Router-level tests for the Movies API.

What these tests do :
- They always override the router's `get_db` dependency so no real Postgres
  connection is ever opened during tests.
- For routes that internally construct `MovieService`, we replace that class
  with a tiny fake so we can control the output.
- For the `GET /{movie_id}` route (which directly queries the DB), we return
  a fake session that mimics the needed SQLAlchemy calls.

Result: fast, deterministic, DB-free tests that still validate the HTTP contract.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, List, Tuple

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.schemas.movie import MovieAvgRatingResponse, MovieListResponse, MovieSchema
from server.routers import movie as movies_router_mod

if TYPE_CHECKING:
    # Only used by type checkers; avoids importing pytest internals at runtime.
    from _pytest.monkeypatch import MonkeyPatch


# ─────────────────────────── Test app & DB override ───────────────────────────

class _NeutralSession:
    """A minimal, neutral fake for the DB session.

    This object is only used to satisfy the router's `get_db` dependency in tests
    where the DB session is not actually touched (because we mock the service).
    """
    pass


@pytest.fixture()
def app() -> FastAPI:
    """Create a FastAPI app that includes only the Movies router.

    We also override the router's `get_db` dependency to yield a neutral fake
    session so tests never open a real database connection.
    """
    app = FastAPI()
    app.include_router(movies_router_mod.router)
    app.dependency_overrides[movies_router_mod.get_db] = lambda: _NeutralSession()
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    """Return a TestClient bound to the minimal test app."""
    return TestClient(app)


# ─────────────────────── Helper for GET /{movie_id} route ─────────────────────

def _fake_db_for_get_movie(found: bool = True) -> Any:
    """Return a fake DB session for the direct-DB route."""

    class _FakeQuery:
        def filter(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
            return self

        def first(self) -> SimpleNamespace | None:
            if found:
                # Minimal object compatible with MovieResponse schema
                return SimpleNamespace(movie_id=1, title="The Matrix")
            return None

    class _FakeSession:
        def query(self, *_args: Any, **_kwargs: Any) -> _FakeQuery:
            return _FakeQuery()

    return _FakeSession()


# ──────────────────────────────── Tests: /{id} ────────────────────────────────

def test_get_movie_200(client: TestClient) -> None:
    """It returns 200 and a MovieResponse when the movie exists."""
    client.app.dependency_overrides[movies_router_mod.get_db] = (
        lambda: _fake_db_for_get_movie(True)
    )

    resp = client.get("/api/rest/v1/movies/1")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"movie_id": 1, "title": "The Matrix"}


def test_get_movie_404(client: TestClient) -> None:
    """It returns 404 when the movie does not exist."""
    client.app.dependency_overrides[movies_router_mod.get_db] = (
        lambda: _fake_db_for_get_movie(False)
    )

    resp = client.get("/api/rest/v1/movies/9999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Movie not found"


# ─────────────────────────────── Tests: GET / ─────────────────────────────────

def test_get_movie_list_200(client: TestClient, monkeypatch: "MonkeyPatch") -> None:
    """It returns a paginated list using a mocked MovieService."""

    class FakeMovieService:
        def __init__(self, _db: Any) -> None:
            # No-op: the route still passes a DB session, but we won't use it.
            pass

        def get_movies_paginated(
            self,
            *,
            page: int,
            limit: int,
            search: str | None,
        ) -> Tuple[List[MovieSchema], int]:
            movies = [
                MovieSchema(movie_id=10, title="Her", genres=[]),
                MovieSchema(movie_id=11, title="Ex Machina", genres=[]),
            ]
            return movies, 42

    # Patch the symbol as imported into the router module.
    monkeypatch.setattr(movies_router_mod, "MovieService", FakeMovieService)

    resp = client.get("/api/rest/v1/movies?page=1&limit=2&search=her")
    assert resp.status_code == 200, resp.text

    # Validate response schema/shape using Pydantic
    body = MovieListResponse.model_validate(resp.json())
    assert body.total == 42
    assert [m.movie_id for m in body.movies] == [10, 11]


def test_get_movie_list_404_when_empty(client: TestClient, monkeypatch: "MonkeyPatch") -> None:
    """It returns 404 when no movies are found for the requested page/search."""

    class FakeMovieService:
        def __init__(self, _db: Any) -> None:
            pass

        def get_movies_paginated(
            self,
            *,
            page: int,
            limit: int,
            search: str | None,
        ) -> Tuple[List[MovieSchema], int]:
            return [], 0

    monkeypatch.setattr(movies_router_mod, "MovieService", FakeMovieService)

    resp = client.get("/api/rest/v1/movies?page=1&limit=10")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No movies found for this page."


# ───────────────────────── Tests: /{id}/avg-rating ────────────────────────────

def test_get_movie_avg_rating_200(client: TestClient, monkeypatch: "MonkeyPatch") -> None:
    """It returns aggregate rating info when the service provides a row.

    We return a simple object with the attributes the route expects (movie_id,
    title, avg_rating, total_ratings).
    """

    class FakeMovieService:
        def __init__(self, _db: Any) -> None:
            pass

        def get_avg_rating(self, movie_id: int) -> SimpleNamespace:
            return SimpleNamespace(
                movie_id=5,
                title="Toy Story",
                avg_rating=4.123456,
                total_ratings=123,
            )

    monkeypatch.setattr(movies_router_mod, "MovieService", FakeMovieService)

    resp = client.get("/api/rest/v1/movies/5/avg-rating")
    assert resp.status_code == 200, resp.text

    body = MovieAvgRatingResponse.model_validate(resp.json())
    assert body.movie_id == 5
    assert body.title == "Toy Story"
    assert body.avg_rating == pytest.approx(4.123456)
    assert body.total_ratings == 123


def test_get_movie_avg_rating_404(client: TestClient, monkeypatch: "MonkeyPatch") -> None:
    """It returns 404 when the service returns no row (missing movie/no ratings)."""

    class FakeMovieService:
        def __init__(self, _db: Any) -> None:
            pass

        def get_avg_rating(self, movie_id: int) -> None:
            return None

    monkeypatch.setattr(movies_router_mod, "MovieService", FakeMovieService)

    resp = client.get("/api/rest/v1/movies/999/avg-rating")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
