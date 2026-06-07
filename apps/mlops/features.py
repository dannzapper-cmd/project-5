"""Statistical window features for EMG and IMU candidate training."""

from __future__ import annotations

import numpy as np


def extract_emg_features(window: np.ndarray) -> np.ndarray:
    """Extract 5-dim feature vector from an EMG signal window."""
    rms = np.sqrt(np.mean(window**2))
    zcr = np.mean(np.diff(np.sign(window)) != 0)
    variance = np.var(window)
    peak2peak = np.max(window) - np.min(window)
    mean_abs = np.mean(np.abs(window))
    return np.array([rms, zcr, variance, peak2peak, mean_abs], dtype=np.float32)


def extract_imu_features(window: np.ndarray) -> np.ndarray:
    """Extract 5-dim feature vector from a 3-axis IMU window (N, 3)."""
    if window.ndim == 1:
        window = window.reshape(-1, 1)
        window = np.pad(window, ((0, 0), (0, 2)), mode="constant")
    magnitude = np.linalg.norm(window, axis=1)
    range_xyz = window.max(axis=0) - window.min(axis=0)
    jerk = np.mean(np.abs(np.diff(magnitude)))
    mean_mag = np.mean(magnitude)
    return np.concatenate([range_xyz, [jerk, mean_mag]]).astype(np.float32)
