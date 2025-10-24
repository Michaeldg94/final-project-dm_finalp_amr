"""Recommendation model training and inference service (NMF + MLflow).

This module provides:
- Training: builds a sparse user–item ratings matrix from the DB, prunes long-tail
  activity, fits an NMF model, and logs a **new** MLflow run with artifacts and metrics.
- Inference: loads the **latest** MLflow run artifacts and returns top-N
  recommendations for a user, with normalized scores that sum to ~1.

Design notes
------------
- Uses CSR sparse matrices to avoid dense allocations for large catalogs.
- Pruning thresholds/caps are configurable to keep training tractable on a single node.
- Artifacts logged:
    - model/W.npy (users × k factors, float32)
    - model/H.npy (k × items factors, float32)
    - model/users.csv (row→user_id mapping)
    - model/items.csv (col→movie_id mapping)
"""

from __future__ import annotations

import os
from typing import List, Tuple

import mlflow
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix, csr_matrix
from sklearn.decomposition import NMF
from sqlalchemy import select
from sqlalchemy.orm import Session

from server.models import RatingModel  # must have: user_id, movie_id, rating

EXPERIMENT_NAME: str = "RecommendationEngine"


def _ensure_experiment() -> str:
    """Ensure the MLflow experiment exists and is set as current.

    Returns
    -------
    str
        The experiment ID (string) for the configured experiment.
    """
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns"))
    exp = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if exp is None:
        exp_id = mlflow.create_experiment(EXPERIMENT_NAME)
    else:
        exp_id = exp.experiment_id
    mlflow.set_experiment(EXPERIMENT_NAME)
    return exp_id


def _fetch_ratings_df(db: Session) -> pd.DataFrame:
    """Fetch ratings as a pandas DataFrame with strict dtypes and validity checks.

    Parameters
    ----------
    db : Session
        Active SQLAlchemy session.

    Returns
    -------
    pandas.DataFrame
        Columns: ['user_id', 'movie_id', 'rating'] with types (int, int, float).
        Filters out nulls and negative ratings.

    Raises
    ------
    ValueError
        If no ratings are found in the database.
    """
    rows = db.execute(
        select(RatingModel.user_id, RatingModel.movie_id, RatingModel.rating)
    ).all()
    if not rows:
        raise ValueError("No ratings found. Ensure the 'ratings' table has data.")
    df = (
        pd.DataFrame(rows, columns=["user_id", "movie_id", "rating"])
        .astype({"user_id": int, "movie_id": int, "rating": float})
        .dropna(subset=["user_id", "movie_id", "rating"])
    )
    # NMF requires non-negative values
    df = df[df["rating"] >= 0]
    return df


def _prune_to_trainable(
    df: pd.DataFrame,
    min_user_ratings: int = 3,
    min_item_ratings: int = 3,
    max_users: int = 120_000,
    max_items: int = 50_000,
) -> pd.DataFrame:
    """Prune long-tail users/items and cap to the most-active slice.

        Iteratively removes users and items with fewer than the minimum number of ratings,
        then caps to top-N most-active users/items to keep training feasible on a single node.

        Parameters
        ----------
        df : pandas.DataFrame
            Input ratings with columns ['user_id', 'movie_id', 'rating'].
        min_user_ratings : int, optional
            Minimum ratings per user to retain, by default 3.
        min_item_ratings : int, optional
            Minimum ratings per item to retain, by default 3.
        max_users : int, optional
            Maximum distinct users to keep (most-active), by default 120_000.
        max_items : int, optional
            Maximum distinct items to keep (most-active), by default 50_000.

        Returns
        -------
        pandas.DataFrame
            Pruned ratings DataFrame (may be empty if thresholds are too strict).
    """
    if df.empty:
        return df

    # Iterative activity filtering
    changed = True
    while changed:
        changed = False
        u_counts = df.groupby("user_id").size()
        i_counts = df.groupby("movie_id").size()
        keep_u = u_counts[u_counts >= min_user_ratings].index
        keep_i = i_counts[i_counts >= min_item_ratings].index
        new_df = df[df["user_id"].isin(keep_u) & df["movie_id"].isin(keep_i)]
        if len(new_df) < len(df):
            df = new_df
            changed = True

    if df.empty:
        return df

    # Cap by activity (most ratings)
    if df["user_id"].nunique() > max_users:
        top_users = (
            df.groupby("user_id").size().sort_values(ascending=False).head(max_users).index
        )
        df = df[df["user_id"].isin(top_users)]

    if df["movie_id"].nunique() > max_items:
        top_items = (
            df.groupby("movie_id").size().sort_values(ascending=False).head(max_items).index
        )
        df = df[df["movie_id"].isin(top_items)]

    return df


def _build_user_item_sparse(df: pd.DataFrame) -> Tuple[csr_matrix, List[int], List[int]]:
    """Build a sparse CSR user–item matrix and ID mappings.

    Parameters
    ----------
    df : pandas.DataFrame
        Ratings with columns ['user_id', 'movie_id', 'rating'] (non-negative).

    Returns
    -------
    tuple[csr_matrix, list[int], list[int]]
        - mat: CSR matrix of shape (num_users, num_items), dtype float32
        - users: list of user IDs in row order
        - items: list of movie IDs in column order
    """
    users = np.sort(df["user_id"].astype(int).unique())
    items = np.sort(df["movie_id"].astype(int).unique())

    user_index = {u: i for i, u in enumerate(users)}
    item_index = {m: i for i, m in enumerate(items)}

    rows = df["user_id"].map(user_index).to_numpy()
    cols = df["movie_id"].map(item_index).to_numpy()
    data = df["rating"].astype(np.float32).to_numpy()  # non-negative ensured above

    mat = coo_matrix(
        (data, (rows, cols)),
        shape = (len(users), len(items)),
        dtype = np.float32,
    ).tocsr()
    return mat, list(users), list(items)


def train_and_log_model(db: Session, n_components: int = 40, random_state: int = 42) -> str:
    """Train NMF on pruned sparse ratings and log a new MLflow run.

    Steps:
    - Fetch ratings and prune long-tail users/items.
    - Build a CSR matrix.
    - Choose k = min(requested_k, num_users, num_items).
    - Fit NMF (CSR supported by scikit-learn).
    - Log artifacts (W, H, users, items) and metrics to MLflow.

    Parameters
    ----------
    db : Session
        Active SQLAlchemy session.
    n_components : int, optional
        Requested latent dimensionality, capped by data shape, by default 40.
    random_state : int, optional
        RNG seed for reproducibility, by default 42.

    Returns
    -------
    str
        The MLflow run ID for the newly logged training run.

    Raises
    ------
    ValueError
        If no data is available after pruning, or data is insufficient.
    """
    _ensure_experiment()

    # Load & prune
    df = _fetch_ratings_df(db)
    df = _prune_to_trainable(
        df,
        min_user_ratings=3,   # tune as you like
        min_item_ratings=3,
        max_users=120_000,    # raise/lower based on your machine
        max_items=50_000,
    )
    if df.empty:
        raise ValueError(
            "After pruning, no ratings remain. Loosen thresholds (min_user_ratings/min_item_ratings) "
            "or increase max_users/max_items."
        )

    # Build sparse matrix
    mat_csr, users, items = _build_user_item_sparse(df)
    num_users, num_items, nnz = len(users), len(items), int(mat_csr.nnz)
    print(f"[RecoTrain] users={num_users} items={num_items} nnz={nnz} requested_k={n_components}")

    # Choose k safely
    k = min(n_components, num_users, num_items)
    if k < 1:
        raise ValueError("Not enough data to train (need ≥1 user and ≥1 item).")

    # Fit NMF (sklearn supports CSR input; factors are dense but small)
    nmf = NMF(
        n_components=k,
        init = "nndsvda",
        random_state = random_state,
        max_iter = 250,
        solver = "cd",
        beta_loss = "frobenius",
    )
    W = nmf.fit_transform(mat_csr)  # shape: (U, k) dense
    H = nmf.components_             # shape: (k, I) dense

    # Log artifacts (float32 is plenty; halves size)
    os.makedirs("artifacts", exist_ok=True)
    np.save("artifacts/W.npy", W.astype(np.float32))
    np.save("artifacts/H.npy", H.astype(np.float32))
    pd.Series(users).to_csv("artifacts/users.csv", index=False, header=False)
    pd.Series(items).to_csv("artifacts/items.csv", index=False, header=False)

    # MLflow run (versioned; never overwrites)
    with mlflow.start_run(run_name=f"nmf-train-k{k}") as run:
        mlflow.log_param("n_components_requested", n_components)
        mlflow.log_param("n_components_used", int(k))
        mlflow.log_metric("num_users", num_users)
        mlflow.log_metric("num_items", num_items)
        mlflow.log_metric("nnz", nnz)

        mlflow.log_artifact("artifacts/W.npy", artifact_path="model")
        mlflow.log_artifact("artifacts/H.npy", artifact_path="model")
        mlflow.log_artifact("artifacts/users.csv", artifact_path="model")
        mlflow.log_artifact("artifacts/items.csv", artifact_path="model")

        return run.info.run_id


def _load_latest_model() -> Tuple[np.ndarray, np.ndarray, List[int], List[int]]:
    """Load the latest MLflow run artifacts for inference.

    Returns
    -------
    tuple[np.ndarray, np.ndarray, list[int], list[int]]
        W (users × k), H (k × items), users (row→user_id), items (col→movie_id).

    Raises
    ------
    RuntimeError
        If no past training runs are found.
    """
    _ensure_experiment()
    client = mlflow.tracking.MlflowClient()
    exp = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    runs = client.search_runs(
        experiment_ids = [exp.experiment_id],
        order_by = ["attributes.start_time DESC"],
        max_results = 1,
    )
    if not runs:
        raise RuntimeError("No training runs found. Train the model first.")
    run = runs[0]
    artifacts_uri = run.info.artifact_uri

    def _local_path(rel: str) -> str:
        if artifacts_uri.startswith("file:"):
            base = artifacts_uri.replace("file:", "")
        else:
            base = artifacts_uri
        return os.path.join(base, rel)

    W = np.load(_local_path("model/W.npy"))
    H = np.load(_local_path("model/H.npy"))
    with open(_local_path("model/users.csv"), "r") as f:
        users = [int(line.strip()) for line in f if line.strip()]
    with open(_local_path("model/items.csv"), "r") as f:
        items = [int(line.strip()) for line in f if line.strip()]
    return W, H, users, items


def recommend_for_user(user_id: int, n: int = 10) -> Tuple[List[int], List[float]]:
    """Return top-N recommended movie IDs and normalized scores for a user.

    Loads the most recent MLflow run, reconstructs item scores for the given user
    (or uses a popularity-based fallback for unseen users), and returns the top-N
    items with min–max normalized scores that sum to ~1.

    Parameters
    ----------
    user_id : int
        The target user ID.
    n : int, optional
        Number of items to return, by default 10.

    Returns
    -------
    tuple[list[int], list[float]]
        - movie_ids: list of item IDs in descending score order
        - probabilities: list of normalized scores summing to ~1
    """
    W, H, users, items = _load_latest_model()
    user_to_row = {u: i for i, u in enumerate(users)}

    if user_id in user_to_row:
        uidx = user_to_row[user_id]
        scores = W[uidx] @ H  # (items,)
    else:
        # cold start: popularity-ish fallback
        scores = H.sum(axis=0)  # (items,)

    idx = np.argsort(scores)[::-1][:n]
    top_items = [int(items[i]) for i in idx]
    top_scores = scores[idx].astype(float)

    # Normalize to probabilities over the top-N
    smin, smax = float(top_scores.min()), float(top_scores.max())
    if smax > smin:
        norm = (top_scores - smin) / (smax - smin)
    else:
        norm = np.ones_like(top_scores)
    probs = norm / norm.sum() if norm.sum() > 0 else np.ones_like(norm) / len(norm)

    return top_items, probs.tolist()
