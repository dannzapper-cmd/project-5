FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install --upgrade pip && \
    pip install "onnxruntime>=1.17.0,<2.0.0" "onnx>=1.14.0,<2.0.0" numpy redis pydantic pydantic-settings

COPY pyproject.toml README.md ./
COPY apps ./apps
COPY models ./models
COPY services/edge-inference/edge_inference ./edge_inference

RUN test -f /app/models/onnx/emg_anomaly_v0.onnx || \
    (echo "ERROR: ONNX models missing. Run make models-generate first." && exit 1)

ENV PYTHONPATH=/app \
    MODEL_DIR=/app/models/onnx \
    METADATA_DIR=/app/models/metadata \
    REDIS_URL=redis://redis:6379/0 \
    MODEL_SCORE_STREAM=axon:v1:stream:model_scores \
    INFERENCE_INTERVAL_MS=500 \
    AXON_PHASE="Phase 2 - Edge AI Core"

CMD ["python", "-m", "edge_inference.main"]
