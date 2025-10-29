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

# ─────────────────────── Tests: get_movies_paginated ─────────────────────────

def test_get_movies_paginated_returns_schemas_and_total(
    monkeypatch: "MonkeyPatch",
    service: MovieService,
) -> None:
    """MovieService.get_movies_paginated maps ORM models to MovieSchema and returns total."""
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
