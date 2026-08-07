FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    DATABASE_PATH=/app/data/bots.db \
    REDIS_URL=redis://127.0.0.1:6379/0 \
    PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-server \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

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
COPY deploy/bothost/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY deploy/bothost/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh \
    && mkdir -p /var/log/supervisor /var/run /app/data

EXPOSE 8080

CMD ["/usr/local/bin/entrypoint.sh"]
