"""Service-level tests for MovieService.

These tests isolate MovieService by monkeypatching the underlying
MovieDataManager methods so no real database is touched.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, List

import pytest

from server.schemas.movie import MovieSchema
from server.services.movie import MovieDataManager, MovieService

if TYPE_CHECKING:
    # Only for static type checkers; avoids importing pytest internals at runtime.
    from _pytest.monkeypatch import MonkeyPatch


# ─────────────────────────── Fixtures & setup ────────────────────────────────

class DummySession:
    """Minimal stand-in for a SQLAlchemy Session expected by MovieService."""
    pass


@pytest.fixture
def service() -> MovieService:
    """Provide a MovieService instance with a dummy session."""
    return MovieService(session=DummySession())


# ───────────────────────────── Tests: get_movie ──────────────────────────────

def test_get_movie_monkeypatched(monkeypatch: "MonkeyPatch", service: MovieService) -> None:
    """MovieService.get_movie returns the schema from the data manager."""
    def fake_get_movie(self: MovieDataManager, movie_id: int) -> MovieSchema:
        return MovieSchema(movie_id=movie_id, title="Matrix", genres=[])

    monkeypatch.setattr(MovieDataManager, "get_movie", fake_get_movie)

    result = service.get_movie(1)
    assert result.title == "Matrix"
    assert result.movie_id == 1


# ───────────────────────────── Tests: get_movies ─────────────────────────────

def test_get_movies_monkeypatched(monkeypatch: "MonkeyPatch", service: MovieService) -> None:
    """MovieService.get_movies returns a list of MovieSchema filtered upstream."""
    def fake_get_movies(self: MovieDataManager, year: int, rating: float) -> List[MovieSchema]:
        # Only populate fields declared in the schema.
        return [
            MovieSchema(movie_id=1, title="A", genres=[]),
            MovieSchema(movie_id=2, title="B", genres=[]),
        ]

    monkeypatch.setattr(MovieDataManager, "get_movies", fake_get_movies)

    result = service.get_movies(year=2020, rating=8.0)
    assert [m.movie_id for m in result] == [1, 2]


# ─────────────────────── Tests: get_movies_paginated ─────────────────────────

def test_get_movies_paginated_returns_schemas_and_total(
    monkeypatch: "MonkeyPatch",
    service: MovieService,
) -> None:
    """MovieService.get_movies_paginated maps ORM models to MovieSchema and returns total."""
    # MovieService expects DataManager.get_movies_paginated -> (models, total)
    # It then maps models to MovieSchema via MovieSchema.model_validate(model)
    # We'll return minimal "model-like" objects with a to_dict() that fits MovieSchema.
    fake_models = [
        SimpleNamespace(
            movie_id=10,
            title="Her",
            genres=[],
            to_dict=lambda: {"movie_id": 10, "title": "Her", "genres": []},
        ),
        SimpleNamespace(
            movie_id=11,
            title="Her 2",
            genres=[],
            to_dict=lambda: {"movie_id": 11, "title": "Her 2", "genres": []},
        ),
    ]

    def fake_get_movies_paginated(
        self: MovieDataManager,
        page: int,
        limit: int,
        search: str | None,
    ):
        return fake_models, 42

    monkeypatch.setattr(MovieDataManager, "get_movies_paginated", fake_get_movies_paginated)

    schemas, total = service.get_movies_paginated(page=1, limit=2, search="her")
    assert total == 42
    assert [s.movie_id for s in schemas] == [10, 11]
    assert all(isinstance(s, MovieSchema) for s in schemas)


# ──────────────────────────── Tests: avg_rating ───────────────────────────────

def test_get_avg_rating_passthrough(monkeypatch: "MonkeyPatch", service: MovieService) -> None:
    """MovieService.get_avg_rating returns the row tuple provided by the data manager."""
    def fake_avg_rating(self: MovieDataManager, movie_id: int):
        # emulate Row(movie_id, title, avg_rating, total_ratings)
        return (movie_id, "Toy Story", 4.1, 1234)

    monkeypatch.setattr(MovieDataManager, "avg_rating", fake_avg_rating)

    row = service.get_avg_rating(5)
    assert row[0] == 5
    assert row[2] == 4.1
