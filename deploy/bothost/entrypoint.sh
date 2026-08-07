#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/data
chmod 777 /app/data 2>/dev/null || true

redis-server --bind 127.0.0.1 --port 6379 --save "" --appendonly no --daemonize yes

echo "Waiting for Redis..."
for _ in $(seq 1 30); do
    if redis-cli -h 127.0.0.1 ping >/dev/null 2>&1; then
        echo "Redis is ready"
        break
    fi
    sleep 0.5
done

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
