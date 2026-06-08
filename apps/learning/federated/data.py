"""Deterministic synthetic, non-IID, biosignal-like datasets for FL clients.

SYNTHETIC ONLY. No real patient data. No clinical datasets are downloaded or
used. No diagnostic validity is implied. Every sample is generated from numpy
RNGs seeded deterministically per client (``client_seed = base_seed +
client_index``), so a fixed seed reproduces the exact same data.

Feature vector (8 dims, order fixed by ``config.FEATURE_NAMES``):
    emg_mean, emg_variance, ecg_mean, ecg_variance,
    imu_magnitude, imu_variance, spo2_mean, spo2_missing_ratio

Labels: 0 = normal, 1 = anomaly. The anomaly pattern differs per client
(non-IID); the global model learns a boundary that generalizes across the
different per-client anomaly signatures.

SpO2 "missing readings" are encoded *safely* via the explicit
``spo2_missing_ratio`` feature (and a correspondingly low ``spo2_mean``), never
as silent NaNs.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from apps.learning.federated.config import FEATURE_NAMES

# Normal-operation baseline (mean, std) per feature. Comparable ~[0, 1] scale so
# the tiny MLP trains stably on CPU without external normalization.
_BASELINE: dict[str, tuple[float, float]] = {
    "emg_mean": (0.30, 0.05),
    "emg_variance": (0.08, 0.02),
    "ecg_mean": (0.50, 0.04),
    "ecg_variance": (0.05, 0.015),
    "imu_magnitude": (0.40, 0.06),
    "imu_variance": (0.07, 0.02),
    "spo2_mean": (0.97, 0.010),
    "spo2_missing_ratio": (0.02, 0.010),
}

# Per-client *normal* baseline offsets make the client distributions distinct
# (non-IID) even before anomalies are added.
_CLIENT_BASELINE_SHIFT: dict[str, dict[str, float]] = {
    "emg_fatigue_noise": {"emg_mean": 0.06, "emg_variance": 0.04},
    "ecg_drift_spike": {"ecg_mean": 0.05, "ecg_variance": 0.02},
    "imu_movement_dropout": {"imu_magnitude": 0.07, "imu_variance": 0.03},
    "spo2_low_missing": {"spo2_mean": -0.03, "spo2_missing_ratio": 0.02},
    "mixed_multi_anomaly": {"emg_mean": 0.03, "imu_magnitude": 0.03},
}

# Anomaly feature shifts per client signal type (added on top of the baseline).
_ANOMALY_SHIFT: dict[str, dict[str, float]] = {
    "emg_fatigue_noise": {"emg_mean": 0.38, "emg_variance": 0.26},
    "ecg_drift_spike": {"ecg_mean": 0.32, "ecg_variance": 0.20},
    "imu_movement_dropout": {"imu_magnitude": 0.42, "imu_variance": 0.26},
    "spo2_low_missing": {"spo2_mean": -0.22, "spo2_missing_ratio": 0.34},
    # Mixed clients draw a random subset of the above per anomaly sample.
    "mixed_multi_anomaly": {},
}

_MIXED_POOL = (
    "emg_fatigue_noise",
    "ecg_drift_spike",
    "imu_movement_dropout",
    "spo2_low_missing",
)


@dataclass
class ClientDataset:
    """A single edge client's synthetic local dataset."""

    client_id: str
    client_index: int
    signal_type: str
    description: str
    features: np.ndarray  # (n, 8) float32
    labels: np.ndarray  # (n,) int64
    seed: int

    @property
    def data_size(self) -> int:
        return int(self.features.shape[0])

    @property
    def anomaly_ratio(self) -> float:
        if self.data_size == 0:
            return 0.0
        return float(np.mean(self.labels == 1))


def _baseline_sample(rng: np.random.Generator, signal_type: str, n: int) -> np.ndarray:
    """Draw ``n`` normal-baseline feature vectors for a client distribution."""
    shift = _CLIENT_BASELINE_SHIFT.get(signal_type, {})
    cols = []
    for name in FEATURE_NAMES:
        mean, std = _BASELINE[name]
        mean = mean + shift.get(name, 0.0)
        cols.append(rng.normal(mean, std, size=n))
    return np.stack(cols, axis=1)


def _apply_anomaly(
    rng: np.random.Generator, base: np.ndarray, signal_type: str
) -> np.ndarray:
    """Apply the client's anomaly shift in-place to a (k, 8) feature block."""
    idx = {name: i for i, name in enumerate(FEATURE_NAMES)}
    if signal_type == "mixed_multi_anomaly":
        for row in range(base.shape[0]):
            picks = rng.choice(_MIXED_POOL, size=rng.integers(1, 3), replace=False)
            for pick in picks:
                for feat, delta in _ANOMALY_SHIFT[pick].items():
                    base[row, idx[feat]] += delta
    else:
        for feat, delta in _ANOMALY_SHIFT[signal_type].items():
            base[:, idx[feat]] += delta
    return base


def generate_client_dataset(
    *,
    client_id: str,
    client_index: int,
    signal_type: str,
    description: str,
    data_size: int,
    anomaly_ratio: float,
    base_seed: int,
) -> ClientDataset:
    """Generate one deterministic synthetic client dataset.

    ``base_seed`` is the experiment seed; the per-client seed is
    ``base_seed + client_index`` (item 7 of the Phase 6A guardrails).
    """
    seed = base_seed + client_index
    rng = np.random.default_rng(seed)

    n_anomaly = int(round(data_size * anomaly_ratio))

    features = _baseline_sample(rng, signal_type, data_size)
    labels = np.zeros(data_size, dtype=np.int64)

    if n_anomaly > 0:
        anomaly_idx = rng.choice(data_size, size=n_anomaly, replace=False)
        block = features[anomaly_idx].copy()
        block = _apply_anomaly(rng, block, signal_type)
        features[anomaly_idx] = block
        labels[anomaly_idx] = 1

    # Clip to a safe, comparable range. spo2_missing_ratio stays in [0, 1].
    features = np.clip(features, -0.5, 2.0).astype(np.float32)

    # Shuffle deterministically so anomalies are not all at the end.
    order = rng.permutation(data_size)
    features = features[order]
    labels = labels[order]

    return ClientDataset(
        client_id=client_id,
        client_index=client_index,
        signal_type=signal_type,
        description=description,
        features=features,
        labels=labels,
        seed=seed,
    )


def build_client_datasets(specs: list[dict], base_seed: int) -> list[ClientDataset]:
    """Build all client datasets from a list of registry specs."""
    return [
        generate_client_dataset(
            client_id=spec["client_id"],
            client_index=spec["client_index"],
            signal_type=spec["signal_type"],
            description=spec["description"],
            data_size=int(spec["data_size"]),
            anomaly_ratio=float(spec["anomaly_ratio"]),
            base_seed=base_seed,
        )
        for spec in specs
    ]


def distribution_summary(datasets: list[ClientDataset]) -> dict:
    """Per-client feature mean/std summary used for evidence + distinctness tests."""
    clients = []
    for ds in datasets:
        clients.append(
            {
                "client_id": ds.client_id,
                "signal_type": ds.signal_type,
                "description": ds.description,
                "data_size": ds.data_size,
                "anomaly_ratio": round(ds.anomaly_ratio, 4),
                "seed": ds.seed,
                "feature_means": {
                    name: round(float(ds.features[:, i].mean()), 5)
                    for i, name in enumerate(FEATURE_NAMES)
                },
                "feature_stds": {
                    name: round(float(ds.features[:, i].std()), 5)
                    for i, name in enumerate(FEATURE_NAMES)
                },
            }
        )
    return {
        "feature_names": list(FEATURE_NAMES),
        "num_clients": len(datasets),
        "clients": clients,
        "synthetic_only": True,
    }
