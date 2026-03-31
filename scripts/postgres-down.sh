#!/usr/bin/env bash
set -euo pipefail

docker rm -f agenticrag-pg >/dev/null 2>&1 || true
echo "agenticrag-pg stopped"
