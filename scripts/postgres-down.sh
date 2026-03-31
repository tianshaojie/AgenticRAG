#!/usr/bin/env bash
set -euo pipefail

docker rm -f agenticrag-pg >/dev/null 2>&1 || true
docker rm -f rag_db >/dev/null 2>&1 || true
echo "PostgreSQL containers stopped (agenticrag-pg, rag_db if present)"
