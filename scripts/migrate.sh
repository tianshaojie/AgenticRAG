#!/usr/bin/env bash
set -euo pipefail

cd backend
source .venv/bin/activate
alembic upgrade head
