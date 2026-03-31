#!/usr/bin/env bash
set -euo pipefail

echo "Development entrypoints:"
echo "  1) make backend-dev   # http://localhost:8000"
echo "  2) make frontend-dev  # http://localhost:5173"
echo
echo "Before first run (local PostgreSQL):"
echo "  make db-setup"
