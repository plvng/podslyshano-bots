FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

COPY pyproject.toml config.yaml ./
COPY src ./src
COPY scripts ./scripts

RUN pip install --no-cache-dir .
