"""Response schema for recommendation results."""

from __future__ import annotations

from typing import List  # if you prefer builtins, you can use list[int], list[float]
from pydantic import BaseModel, ConfigDict, Field, model_validator


class RecommendResponse(BaseModel):
    """Top-N movie recommendations for a user.

    Attributes
    ----------
    movie_ids : List[int]
        Movie IDs ordered from most to least relevant.
    probabilities : List[float]
        Normalized relevance scores aligned with `movie_ids`.
        Must be non-negative and (approximately) sum to 1.
    """

    movie_ids: List[int] = Field(
        ...,
        description = "Movie IDs ordered by descending relevance.",
        min_length = 1,
    )
    probabilities: List[float] = Field(
        ...,
        description = "Normalized scores aligned with `movie_ids` (sum approx. 1).",
        min_length = 1,
    )

    model_config = ConfigDict(
        from_attributes = True,
        json_schema_extra = {
            "example": {
                "movie_ids": [12, 7, 33, 5, 18],
                "probabilities": [0.22, 0.19, 0.17, 0.22, 0.20],
            }
        },
    )

    @model_validator(mode="after")
    def _validate_lengths_and_probs(self) -> "RecommendResponse":
        """Ensure lengths match, values are non-negative, and sum ≈ 1."""
        if len(self.movie_ids) != len(self.probabilities):
            raise ValueError("`movie_ids` and `probabilities` must have the same length.")

        if any(p < 0 for p in self.probabilities):
            raise ValueError("All `probabilities` must be non-negative.")

        total = sum(self.probabilities)
        # allow tiny numeric noise
        if not (0.999 <= total <= 1.001):
            raise ValueError("`probabilities` must sum to ~1.0.")
        return self
