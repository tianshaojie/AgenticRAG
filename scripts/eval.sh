#!/usr/bin/env bash
set -euo pipefail

DATASET="${1:-golden_v1}"
RUN_NAME="${2:-manual-eval}"

cd backend
source .venv/bin/activate
python -m app.evals.cli --dataset "${DATASET}" --name "${RUN_NAME}"
