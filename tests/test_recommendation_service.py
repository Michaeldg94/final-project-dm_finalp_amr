"""Service-level tests for the recommendation helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

import numpy as np
import pandas as pd
import pytest

from server.services.recommendation import (
    _build_user_item_sparse,
    _prune_to_trainable,
    recommend_for_user,
)

if TYPE_CHECKING:  # for static type checkers only; no runtime dependency on _pytest.*
    from _pytest.monkeypatch import MonkeyPatch


# ─────────────────────────── Tests: _prune_to_trainable ───────────────────────

def test_prune_to_trainable_filters_and_caps() -> None:
    """It removes users/items below thresholds and preserves those meeting them."""
    df: pd.DataFrame = pd.DataFrame(
        {
            "user_id": [1, 1, 2, 2, 2, 3],
            "movie_id": [10, 11, 10, 11, 12, 10],
            "rating": [4, 5, 3, 4, 5, 2],
        }
    )
    pruned: pd.DataFrame = _prune_to_trainable(df, min_user_ratings=2, min_item_ratings=2)

    # user 3 only had one rating -> dropped; movie 12 had one rating -> dropped
    assert set(pruned["user_id"]) == {1, 2}
    assert set(pruned["movie_id"]) == {10, 11}


# ───────────────────────── Tests: _build_user_item_sparse ─────────────────────

def test_build_user_item_sparse_shapes_and_ordering() -> None:
    """It builds a CSR matrix with sorted unique users/items and correct values."""
    df: pd.DataFrame = pd.DataFrame(
        {
            "user_id": [2, 1, 2],
            "movie_id": [10, 10, 11],
            "rating": [3.0, 4.0, 5.0],
        }
    )
    mat, users, items = _build_user_item_sparse(df)

    # users/items are sorted unique
    assert users == [1, 2]
    assert items == [10, 11]
    assert mat.shape == (2, 2)
    # user 1, movie 10 = 4.0
    assert mat[0, 0] == 4.0
    # user 2, movie 11 = 5.0
    assert mat[1, 1] == 5.0


# ───────────────────── Tests: recommend_for_user (hot start) ──────────────────

def test_recommend_for_user_uses_loaded_model(monkeypatch: "MonkeyPatch") -> None:
    """Hot-start path: uses W @ H for a known user and returns normalized top-N."""
    # Fake a tiny model: users=[100], items=[10, 11, 12]
    # W: (1,k), H: (k,3) -> scores = W @ H -> (3,)
    W: np.ndarray = np.array([[1.0, 0.5]], dtype=float)
    H: np.ndarray = np.array(
        [
            [0.2, 0.1, 0.3],
            [0.0, 0.4, 0.1],
        ],
        dtype=float,
    )
    users: List[int] = [100]
    items: List[int] = [10, 11, 12]

    def fake_load_latest_model() -> Tuple[np.ndarray, np.ndarray, List[int], List[int]]:
        return W, H, users, items

    # Patch the module that recommend_for_user imports from
    from server.services import recommendation as reco_mod

    monkeypatch.setattr(reco_mod, "_load_latest_model", fake_load_latest_model)

    top_items, probs = reco_mod.recommend_for_user(user_id=100, n=2)
    # scores = [0.2, 0.3, 0.35] -> top2 indices: 12, 11
    assert top_items == [12, 11]
    assert len(probs) == 2
    assert pytest.approx(sum(probs), rel=1e-6) == 1.0


# ───────────────────── Tests: recommend_for_user (cold start) ─────────────────

def test_recommend_for_user_cold_start(monkeypatch: "MonkeyPatch") -> None:
    """Cold-start path: falls back to popularity-ish sum over H rows."""
    W: np.ndarray = np.zeros((0, 0))  # unused in cold start
    # H rows sum -> column sums [0.3, 0.1]
    H: np.ndarray = np.array(
        [
            [0.2, 0.1],
            [0.1, 0.0],
        ],
        dtype=float,
    )
    users: List[int] = [999]  # not our user
    items: List[int] = [10, 11]

    def fake_load_latest_model() -> Tuple[np.ndarray, np.ndarray, List[int], List[int]]:
        return W, H, users, items

    from server.services import recommendation as reco_mod

    monkeypatch.setattr(reco_mod, "_load_latest_model", fake_load_latest_model)

    top_items, probs = reco_mod.recommend_for_user(user_id=12345, n=1)
    assert top_items == [10]
    assert pytest.approx(sum(probs), rel=1e-6) == 1.0
