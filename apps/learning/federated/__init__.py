"""Phase 6A — Federated Learning simulation (Flower + FedAvg, synthetic data).

This package simulates multiple edge nodes ("edge clients") that each train a
tiny CPU MLP (:class:`~apps.learning.federated.model.AxonFLModelV1`) on their own
synthetic, non-IID, biosignal-like dataset. A central coordinator aggregates the
updates with Flower's FedAvg strategy. Everything is deterministic (fixed seeds),
local-first, and logged to a local file-based MLflow tracking store.

SAFETY / SCOPE
--------------
- Synthetic federated learning simulation. No real patient data. No medical claims.
- Not medical diagnosis. Not clinical monitoring. Not trained on real patients.
- Output is an operational/anomaly *simulation* only.
- Phase 6A only — this package does NOT implement RL (Phase 6B) or Phase 7.
"""

from apps.learning.federated.disclaimer import DISCLAIMER

__all__ = ["DISCLAIMER"]
