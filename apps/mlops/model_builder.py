"""Candidate model builder (LogisticRegression pipeline)."""

from __future__ import annotations

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def build_candidate_model() -> Pipeline:
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    max_iter=200,
                    random_state=42,
                    C=1.0,
                    solver="lbfgs",
                ),
            ),
        ]
    )
