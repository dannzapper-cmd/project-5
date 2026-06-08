# AXON Phase 6B — RL micro-module runner (Docker `learning` profile only).
#
# This image is NOT part of the core profile and is never required for the core
# demo. It runs ONE RL experiment on demand (a one-shot `rl-runner`), writes
# evidence artifacts, and logs an MLflow run to the local file store.
#
# Synthetic RL operational policy. No real patient data. No medical decisions.
# Human review required for high-risk actions.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# CPU-only torch + Gymnasium + Stable-Baselines3 + MLflow file store. Heavy deps
# stay isolated to this image; core images never install them.
COPY requirements-rl.txt ./requirements-rl.txt
RUN pip install --upgrade pip && \
    pip install "torch>=2.2,<3.0" --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements-rl.txt

COPY pyproject.toml README.md ./
COPY apps ./apps
COPY scripts ./scripts

# Defaults can be overridden by the compose service / env.
ENV RL_SEED=42 \
    RL_TOTAL_TIMESTEPS=15000 \
    RL_EVAL_EPISODES=100 \
    MLFLOW_TRACKING_URI=file:///app/artifacts/mlops/mlruns

CMD ["sh", "-c", "python scripts/run_rl_micro_module.py --seed ${RL_SEED} --total-timesteps ${RL_TOTAL_TIMESTEPS} --eval-episodes ${RL_EVAL_EPISODES}"]
