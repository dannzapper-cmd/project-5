"""Sliding-window confidence-based drift detector."""

from __future__ import annotations

from collections import deque

import numpy as np

from apps.mlops.config import DRIFT_THRESHOLD, DRIFT_WINDOW


class SlidingWindowDriftDetector:
    def __init__(self, window: int = DRIFT_WINDOW, threshold: float = DRIFT_THRESHOLD):
        self.window = window
        self.threshold = threshold
        self._scores: deque[float] = deque(maxlen=window)

    def update(self, confidence: float) -> None:
        self._scores.append(confidence)

    def check(self) -> dict:
        if len(self._scores) < self.window:
            return {
                "drift_status": "insufficient_data",
                "drift_score": None,
                "threshold": self.threshold,
                "evidence_window": len(self._scores),
                "mean_confidence": None,
                "recommendation": "continue_monitoring",
                "synthetic_only": True,
                "safety_notes": "Simulated drift detection only. No clinical inference.",
            }
        mean_conf = float(np.mean(self._scores))
        drifted = mean_conf < self.threshold
        return {
            "drift_status": "drift_detected" if drifted else "nominal",
            "drift_score": round(1.0 - mean_conf, 4),
            "threshold": self.threshold,
            "evidence_window": self.window,
            "mean_confidence": round(mean_conf, 4),
            "recommendation": "evaluate_candidate_model" if drifted else "continue_monitoring",
            "synthetic_only": True,
            "safety_notes": "Simulated drift detection only. No clinical inference.",
        }

    def reset(self) -> None:
        self._scores.clear()
