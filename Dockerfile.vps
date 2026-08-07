FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

RUN pip install --no-cache-dir \
    "aiogram>=3.13,<4" \
    "pydantic-settings>=2.0" \
    "redis>=5.0" \
    "aiosqlite>=0.20" \
    "PyYAML>=6.0" \
    "fastapi>=0.115" \
    "uvicorn[standard]>=0.32" \
    "jinja2>=3.1" \
    "python-multipart>=0.0.12"

COPY config.yaml ./
COPY src ./src
COPY scripts ./scripts
