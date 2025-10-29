# tests/test_movies_router.py
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.schemas.movie import MovieAvgRatingResponse, MovieListResponse
from server.routers import movie as movies_router_mod


# ──────────────────────────── Fake DB machinery ──────────────────────────────

class _FakeQuery:
    """Tiny SQLAlchemy-like query facade for the list endpoint."""
    def __init__(self, rows: List[Any]) -> None:
        self._rows = rows
        self._start = 0
        self._stop: int | None = None

    # We won't use join/filter/distinct in these tests (we call the route without `search`),
    # but we keep them here as no-ops so the object is resilient if needed later.
    def join(self, *_a, **_k): return self
    def filter(self, *_a, **_k): return self
    def distinct(self): return self

    def count(self) -> int:
        return len(self._rows)

    def offset(self, n: int) -> "_FakeQuery":
        self._start = n
        return self

    def limit(self, n: int) -> "_FakeQuery":
        self._stop = self._start + n
        return self

    def all(self) -> List[Any]:
        if self._stop is None:
            return self._rows[self._start :]
        return self._rows[self._start : self._stop]


class _FakeSession:
    """Yields a query object seeded with the rows we want the endpoint to see."""
    def __init__(self, rows: List[Any]) -> None:
        self._rows = rows

    def query(self, *_args: Any, **_kwargs: Any) -> _FakeQuery:
        return _FakeQuery(self._rows)


def _movie_row(movie_id: int, title: str) -> Any:
    # Minimal shape that Pydantic can read as ORM (MovieSchema) via from_attributes
    return SimpleNamespace(movie_id=movie_id, title=title, genres=[])


# ───────────────────────────── App / client fixtures ─────────────────────────

@pytest.fixture()
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(movies_router_mod.router)
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


# ───────────────────────────── Tests: GET / (list) ───────────────────────────

def test_get_movie_list_200(client: TestClient) -> None:
    """Returns a paginated list with total count, no real DB."""
    # Seed 5 movies; request page=1, limit=2 should return first 2 and total=5
    rows = [
        _movie_row(1, "The Matrix"),
        _movie_row(2, "The Matrix Reloaded"),
        _movie_row(3, "The Matrix Revolutions"),
        _movie_row(4, "The Animatrix"),
        _movie_row(5, "John Wick"),
    ]

    client.app.dependency_overrides[movies_router_mod.get_db] = lambda: _FakeSession(rows)

    resp = client.get("/api/rest/v1/movies?page=1&limit=2")
    assert resp.status_code == 200, resp.text

    body = MovieListResponse.model_validate(resp.json())
    assert body.total == 5
    # The router returns the first 2 items for page=1,limit=2
    assert [m.movie_id for m in body.movies] == [1, 2]


def test_get_movie_list_404_when_empty(client: TestClient) -> None:
    """404 when the page is empty (no movies)."""
    client.app.dependency_overrides[movies_router_mod.get_db] = lambda: _FakeSession([])

    resp = client.get("/api/rest/v1/movies?page=1&limit=10")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No movies found for this page."


# ───────────────────────── Tests: GET /{id}/avg-rating ───────────────────────

def test_get_movie_avg_rating_200(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns aggregate rating info using a mocked MovieService."""

    class FakeMovieService:
        def __init__(self, _db: Any) -> None:
            pass

        def get_avg_rating(self, movie_id: int) -> SimpleNamespace:
            assert movie_id == 5
            return SimpleNamespace(
                movie_id=5,
                title="Toy Story",
                avg_rating=4.123456,
                total_ratings=123,
            )

    # Provide a neutral DB override (service doesn't use it here)
    client.app.dependency_overrides[movies_router_mod.get_db] = lambda: object()
    monkeypatch.setattr(movies_router_mod, "MovieService", FakeMovieService)

    resp = client.get("/api/rest/v1/movies/5/avg-rating")
    assert resp.status_code == 200, resp.text

    body = MovieAvgRatingResponse.model_validate(resp.json())
    assert body.movie_id == 5
    assert body.title == "Toy Story"
    assert body.avg_rating == pytest.approx(4.123456)
    assert body.total_ratings == 123


def test_get_movie_avg_rating_404(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """404 when the service returns None (movie missing / no ratings)."""

    class FakeMovieService:
        def __init__(self, _db: Any) -> None:
            pass

        def get_avg_rating(self, movie_id: int) -> None:
            return None

    client.app.dependency_overrides[movies_router_mod.get_db] = lambda: object()
    monkeypatch.setattr(movies_router_mod, "MovieService", FakeMovieService)

    resp = client.get("/api/rest/v1/movies/999/avg-rating")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
