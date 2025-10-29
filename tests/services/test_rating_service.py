"""Service-level tests for RatingService.

These tests monkeypatch the data-access layer (RatingDataManager) so we
can verify the service behavior without hitting a real database.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from server.schemas.ratings import RatingCreate, RatingResponse
from server.services.ratings import RatingDataManager, RatingService

if TYPE_CHECKING:
    # Only for static type checkers; avoids importing pytest internals at runtime.
    from _pytest.monkeypatch import MonkeyPatch


# ─────────────────────────── Fixtures & setup ────────────────────────────────

class DummySession:
    """Minimal stand-in for a SQLAlchemy Session expected by the service."""
    pass


# ────────────────────────────── Happy path ───────────────────────────────────

def test_rating_service_success(monkeypatch: "MonkeyPatch") -> None:
    """RatingService.create_rating returns the data manager result on success."""
    svc = RatingService(session=DummySession())

    def fake_create_rating(self: RatingDataManager, payload: RatingCreate) -> RatingResponse:
        """Fake implementation that mimics a successful DB insert."""
        return RatingResponse(
            rating_id=100,
            user_id=payload.user_id,
            movie_id=payload.movie_id,
            rating=payload.rating,
            timestamp=datetime.now(UTC),  # timezone-aware
        )

    monkeypatch.setattr(RatingDataManager, "create_rating", fake_create_rating)

    payload = RatingCreate(user_id=1, movie_id=2, rating=4.5)
    res = svc.create_rating(payload)
    assert res.rating_id == 100
    assert res.user_id == 1
    assert res.movie_id == 2
    assert res.rating == 4.5
    assert res.timestamp.tzinfo is not None


# ───────────────────────────── Error handling ────────────────────────────────

@pytest.mark.parametrize(
    "error_message",
    ["Movie not found", "User not found", "User already rated this movie"],
)
def test_rating_service_bubbles_up_validation_errors(
    monkeypatch: "MonkeyPatch",
    error_message: str,
) -> None:
    """Service should propagate ValueError messages from the data layer."""
    svc = RatingService(session=DummySession())

    def fake_create_rating(self: RatingDataManager, payload: RatingCreate) -> RatingResponse:
        raise ValueError(error_message)

    monkeypatch.setattr(RatingDataManager, "create_rating", fake_create_rating)

    with pytest.raises(ValueError) as ei:
        svc.create_rating(RatingCreate(user_id=1, movie_id=2, rating=3.0))
    assert error_message in str(ei.value)
