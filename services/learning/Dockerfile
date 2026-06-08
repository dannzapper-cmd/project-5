# AXON Phase 6A — Federated Learning runner (Docker `learning` profile only).
#
# This image is NOT part of the core profile and is never required for the core
# demo. It runs ONE federated experiment on demand (a one-shot `fl-runner`),
# writes evidence artifacts, and logs an MLflow run to the local file store.
#
# Synthetic federated learning simulation. No real patient data. No medical claims.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# CPU-only torch + Flower 1.x (simulation) + MLflow file store. Heavy deps stay
# isolated to this image; core images never install them.
COPY requirements-learning.txt ./requirements-learning.txt
RUN pip install --upgrade pip && \
    pip install "torch>=2.2,<3.0" --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements-learning.txt

COPY pyproject.toml README.md ./
COPY apps ./apps
COPY scripts ./scripts

# Defaults can be overridden by the compose service / env.
ENV FL_SEED=42 \
    FL_NUM_CLIENTS=3 \
    FL_NUM_ROUNDS=5 \
    FL_LOCAL_EPOCHS=3 \
    MLFLOW_TRACKING_URI=file:///app/artifacts/mlops/mlruns

CMD ["sh", "-c", "python scripts/run_federated_learning.py --num-clients ${FL_NUM_CLIENTS} --num-rounds ${FL_NUM_ROUNDS} --local-epochs ${FL_LOCAL_EPOCHS} --seed ${FL_SEED}"]
