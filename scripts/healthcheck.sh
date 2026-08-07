#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

services=(redis proposal-bot chat-bot admin-web)
for service in "${services[@]}"; do
  if ! docker compose ps --status running --services | grep -qx "$service"; then
    echo "Service not running: $service"
    exit 1
  fi
done

docker compose exec redis redis-cli ping >/dev/null
curl -fsS "http://127.0.0.1:8080/login" >/dev/null
echo "All services OK"
