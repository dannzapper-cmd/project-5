FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY apps ./apps
COPY scripts ./scripts
COPY services/sensor-generators ./services/sensor-generators

RUN pip install --upgrade pip && pip install .

CMD ["python", "-m", "axon_generators"]
