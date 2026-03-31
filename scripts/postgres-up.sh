#!/usr/bin/env bash
set -euo pipefail

NAME="agenticrag-pg"
PORT="${PG_PORT:-5432}"
IMAGE="${PGVECTOR_IMAGE:-pgvector/pgvector:pg16}"

docker run --rm -d \
  --name "$NAME" \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=agentic_rag \
  -p "$PORT":5432 \
  "$IMAGE"

for _ in {1..60}; do
  if docker exec "$NAME" pg_isready -U postgres -d agentic_rag >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! docker exec "$NAME" pg_isready -U postgres -d agentic_rag >/dev/null 2>&1; then
  echo "PostgreSQL did not become ready in time" >&2
  exit 1
fi

echo "PostgreSQL + pgvector started: postgresql://postgres:postgres@127.0.0.1:${PORT}/agentic_rag"
