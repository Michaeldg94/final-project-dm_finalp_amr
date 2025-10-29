# tests/routers/test_movies_router.py
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List, Tuple, TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.schemas.movie import MovieAvgRatingResponse, MovieListResponse, MovieSchema
from server.routers import movie as movies_router_mod

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


# ──────────────────────────── Test app & DB override ─────────────────────────

class _NeutralSession:
    """Neutral fake session: only used to satisfy get_db in tests."""
    pass


@pytest.fixture()
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(movies_router_mod.router)
    # Never open a real DB connection during tests
    app.dependency_overrides[movies_router_mod.get_db] = lambda: _NeutralSession()
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


# ───────────────────────────── Tests: GET / ──────────────────────────────────

def test_get_movie_list_200(client: TestClient, monkeypatch: "MonkeyPatch") -> None:
    """GET / returns a paginated list via mocked MovieService."""

    class FakeMovieService:
        def __init__(self, _db: Any) -> None:
            pass

        def get_movies_paginated(
            self, *, page: int, limit: int, search: str | None
        ) -> Tuple[List[MovieSchema], int]:
            assert page == 1
            assert limit == 2
            assert search == "her"
            movies = [
                MovieSchema(movie_id=10, title="Her", genres=[]),
                MovieSchema(movie_id=11, title="Ex Machina", genres=[]),
            ]
            return movies, 42

    # Patch the symbol as imported into the router module
    monkeypatch.setattr(movies_router_mod, "MovieService", FakeMovieService)

    resp = client.get("/api/rest/v1/movies?page=1&limit=2&search=her")
    assert resp.status_code == 200, resp.text

    # Validate via Pydantic schema
    body = MovieListResponse.model_validate(resp.json())
    assert body.total == 42
    assert [m.movie_id for m in body.movies] == [10, 11]


def test_get_movie_list_404_when_empty(client: TestClient, monkeypatch: "MonkeyPatch") -> None:
    """GET / returns 404 when service returns no movies."""

    class FakeMovieService:
        def __init__(self, _db: Any) -> None:
            pass

        def get_movies_paginated(
            self, *, page: int, limit: int, search: str | None
        ) -> Tuple[List[MovieSchema], int]:
            return [], 0

    monkeypatch.setattr(movies_router_mod, "MovieService", FakeMovieService)

    resp = client.get("/api/rest/v1/movies?page=1&limit=10")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No movies found for this page."


# ───────────────────────── Tests: /{id}/avg-rating ───────────────────────────

def test_get_movie_avg_rating_200(client: TestClient, monkeypatch: "MonkeyPatch") -> None:
    """GET /{id}/avg-rating returns aggregate rating info when service provides a row."""

    class FakeMovieService:
        def __init__(self, _db: Any) -> None:
            pass

        def get_avg_rating(self, movie_id: int):
            assert movie_id == 5
            # Minimal row-like object with expected attributes
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
    """GET /{id}/avg-rating returns 404 when service returns None."""

    class FakeMovieService:
        def __init__(self, _db: Any) -> None:
            pass

        def get_avg_rating(self, movie_id: int):
            return None

    monkeypatch.setattr(movies_router_mod, "MovieService", FakeMovieService)

    resp = client.get("/api/rest/v1/movies/999/avg-rating")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
