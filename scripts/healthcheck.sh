#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! docker compose ps --services --filter status=running | grep -q .; then
  echo "No running containers"
  exit 1
fi

docker compose ps
docker compose exec redis redis-cli ping >/dev/null
echo "OK"
