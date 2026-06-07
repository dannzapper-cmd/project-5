"""AxonFLModelV1 — a tiny CPU-friendly MLP for synthetic anomaly classification.

Architecture (item 6 of the Phase 6A guardrails):
    input_dim = 8  ->  Linear(8, 32) -> ReLU
                  ->  Linear(32, 16) -> ReLU
                  ->  Linear(16, 2)            (0 = normal, 1 = anomaly)

Total trainable parameters: 8*32+32 + 32*16+16 + 16*2+2 = 850 (< 1000).

No CNN/Transformer/large model. This is an operational/anomaly *simulation*
classifier on synthetic data only — no medical claims, no diagnosis.
"""

from __future__ import annotations

import random
from collections import OrderedDict

import numpy as np
import torch
from torch import nn

from apps.learning.federated.config import HIDDEN_LAYERS, INPUT_DIM, OUTPUT_DIM


class AxonFLModelV1(nn.Module):
    """Tiny MLP classifier shared by every federated edge client."""

    def __init__(self) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        prev = INPUT_DIM
        for hidden in HIDDEN_LAYERS:
            layers.append(nn.Linear(prev, hidden))
            layers.append(nn.ReLU())
            prev = hidden
        layers.append(nn.Linear(prev, OUTPUT_DIM))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def count_parameters(model: nn.Module | None = None) -> int:
    """Total number of trainable parameters (used by tests + reports)."""
    model = model or AxonFLModelV1()
    return int(sum(p.numel() for p in model.parameters() if p.requires_grad))


def set_seed(seed: int) -> None:
    """Seed every RNG that affects training (item 7 — reproducibility)."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.backends.cudnn.is_available():  # pragma: no cover - CPU CI
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def get_parameters(model: nn.Module) -> list[np.ndarray]:
    """Extract model weights as a list of numpy arrays (Flower NDArrays)."""
    return [val.detach().cpu().numpy() for _, val in model.state_dict().items()]


def set_parameters(model: nn.Module, parameters: list[np.ndarray]) -> None:
    """Load a list of numpy arrays into the model (Flower NDArrays -> state)."""
    params_dict = zip(model.state_dict().keys(), parameters, strict=True)
    state_dict = OrderedDict(
        {k: torch.tensor(np.asarray(v), dtype=torch.float32) for k, v in params_dict}
    )
    model.load_state_dict(state_dict, strict=True)


def train_local(
    model: nn.Module,
    features: np.ndarray,
    labels: np.ndarray,
    *,
    epochs: int,
    lr: float,
    seed: int,
    batch_size: int = 32,
) -> float:
    """Train the model in-place on one client's data with mini-batch SGD.

    Each epoch is a full deterministic pass over the client's data in shuffled
    mini-batches, giving enough gradient steps for meaningful FedAvg convergence
    at small epoch/round counts while staying CPU-fast. Returns final batch loss.
    """
    set_seed(seed)
    model.train()
    x = torch.tensor(features, dtype=torch.float32)
    y = torch.tensor(labels, dtype=torch.long)
    optimizer = torch.optim.SGD(model.parameters(), lr=lr, momentum=0.9)
    criterion = nn.CrossEntropyLoss()
    generator = torch.Generator().manual_seed(seed)

    n = x.shape[0]
    bs = max(1, min(batch_size, n))
    last_loss = 0.0
    for _ in range(max(1, epochs)):
        perm = torch.randperm(n, generator=generator)
        for start in range(0, n, bs):
            idx = perm[start : start + bs]
            optimizer.zero_grad()
            loss = criterion(model(x[idx]), y[idx])
            loss.backward()
            optimizer.step()
            last_loss = float(loss.detach())
    return last_loss


def evaluate(
    model: nn.Module, features: np.ndarray, labels: np.ndarray
) -> tuple[float, float]:
    """Return (loss, accuracy) on a feature/label set."""
    model.eval()
    x = torch.tensor(features, dtype=torch.float32)
    y = torch.tensor(labels, dtype=torch.long)
    criterion = nn.CrossEntropyLoss()
    with torch.no_grad():
        logits = model(x)
        loss = float(criterion(logits, y))
        preds = torch.argmax(logits, dim=1)
        accuracy = float((preds == y).float().mean())
    return loss, accuracy
