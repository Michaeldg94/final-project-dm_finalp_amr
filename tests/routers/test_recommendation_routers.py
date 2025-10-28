"""Router-level tests for the Recommendation endpoints."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, List, Tuple

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.routers import recommendation as reco_router_mod
from server.schemas.recommendation import RecommendResponse

if TYPE_CHECKING:
    # Only for static type checkers; avoids importing pytest internals at runtime.
    from _pytest.monkeypatch import MonkeyPatch


# ─────────────────────────── App / client fixtures ───────────────────────────

@pytest.fixture()
def app() -> FastAPI:
    """Create a minimal FastAPI app with just the Recommendation router attached."""
    app = FastAPI()
    app.include_router(reco_router_mod.router)
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    """Return a TestClient bound to the minimal test app."""
    return TestClient(app)


# ─────────────────────────── Background task tests ───────────────────────────

def test_submit_and_poll_training_success(client: TestClient, monkeypatch: "MonkeyPatch") -> None:
    """Happy path: submit returns 202 + task_id; polling reaches 'done' with run_id."""
    # Provide a fast trainer that returns a known run_id without touching MLflow.
    def fake_trainer(_db: Any) -> str:
        return "fake-run-id"

    # Provide a fake session manager so the background task doesn't open a real DB.
    class FakeSM:
        def open_session(self):
            class _Ctx:
                def __enter__(self): return object()
                def __exit__(self, *args): return False
            return _Ctx()

    client.app.dependency_overrides[reco_router_mod.get_trainer] = lambda: fake_trainer
    client.app.dependency_overrides[reco_router_mod.get_session_manager] = lambda: FakeSM()

    # Submit the training job
    submit = client.post("/api/rest/v1/recommendation-engine")
    assert submit.status_code == 202, submit.text
    body = submit.json()
    assert set(body.keys()) == {"task_id", "status"}
    assert body["status"] == "queued"
    task_id = body["task_id"]

    # Poll until the task reaches "done"
    final = None
    for _ in range(20):
        poll = client.get(f"/api/rest/v1/recommendation-engine/{task_id}")
        assert poll.status_code == 200
        state = poll.json()
        if state["status"] == "done":
            final = state
            break
        time.sleep(0.02)  # tiny backoff

    assert final is not None, "Background training never reached 'done'"
    assert final["run_id"] == "fake-run-id"


def test_training_error_is_reported(client: TestClient, monkeypatch: "MonkeyPatch") -> None:
    """If the trainer raises, the task becomes 'error' and exposes the message."""
    def boom(_db: Any) -> str:
        raise RuntimeError("kaboom")

    class FakeSM:
        def open_session(self):
            class _Ctx:
                def __enter__(self): return object()
                def __exit__(self, *args): return False
            return _Ctx()

    client.app.dependency_overrides[reco_router_mod.get_trainer] = lambda: boom
    client.app.dependency_overrides[reco_router_mod.get_session_manager] = lambda: FakeSM()

    submit = client.post("/api/rest/v1/recommendation-engine")
    assert submit.status_code == 202, submit.text
    task_id = submit.json()["task_id"]

    # Poll until the task reports "error"
    err_msg = None
    for _ in range(20):
        poll = client.get(f"/api/rest/v1/recommendation-engine/{task_id}")
        assert poll.status_code == 200
        state = poll.json()
        if state["status"] == "error":
            err_msg = state.get("error")
            break
        time.sleep(0.02)

    assert err_msg is not None and "kaboom" in err_msg


# ─────────────────────────── Inference endpoint tests ───────────────────────────

def test_get_recommended_movies_200(client: TestClient, monkeypatch: "MonkeyPatch") -> None:
    """GET recommended movies returns 200 and matches the response schema."""
    def fake_recommend_for_user(user_id: int, n: int) -> Tuple[List[int], List[float]]:
        return [10, 11], [0.6, 0.4]

    # Important: the router imports the function directly, so patch the router module.
    monkeypatch.setattr(reco_router_mod, "recommend_for_user", fake_recommend_for_user)

    resp = client.get("/api/rest/v1/user/123/recommended-movies?n=2")
    assert resp.status_code == 200, resp.text

    payload = RecommendResponse.model_validate(resp.json())
    assert payload.movie_ids == [10, 11]
    assert payload.probabilities == [0.6, 0.4]
    assert abs(sum(payload.probabilities) - 1.0) < 1e-6


def test_get_recommended_movies_500_on_exception(client: TestClient, monkeypatch: "MonkeyPatch") -> None:
    """Service exceptions are surfaced as HTTP 500 with the error detail."""
    def boom(_user_id: int, _n: int) -> Tuple[List[int], List[float]]:
        raise RuntimeError("no trained model")

    monkeypatch.setattr(reco_router_mod, "recommend_for_user", boom)

    resp = client.get("/api/rest/v1/user/1/recommended-movies?n=2")
    assert resp.status_code == 500
    assert "no trained model" in resp.json()["detail"]


def test_get_recommended_movies_422_on_bad_n(client: TestClient) -> None:
    """Validation: 'n' must be gt=0 and le=100; 0 should trigger a 422."""
    resp = client.get("/api/rest/v1/user/1/recommended-movies?n=0")
    assert resp.status_code == 422
