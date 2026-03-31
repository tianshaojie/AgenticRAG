SHELL := /bin/zsh

BACKEND_DIR := backend
FRONTEND_DIR := frontend

.PHONY: backend-install frontend-install install backend-dev frontend-dev dev backend-test frontend-test test integration-test smoke-test lint format alembic-upgrade alembic-revision

install: backend-install frontend-install

backend-install:
	cd $(BACKEND_DIR) && python3 -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'

frontend-install:
	cd $(FRONTEND_DIR) && npm install

backend-dev:
	cd $(BACKEND_DIR) && source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev:
	cd $(FRONTEND_DIR) && npm run dev -- --host 0.0.0.0 --port 5173

dev:
	@echo "Run backend-dev and frontend-dev in separate terminals"

backend-test:
	cd $(BACKEND_DIR) && source .venv/bin/activate && pytest -q

frontend-test:
	cd $(FRONTEND_DIR) && npm run test

test: backend-test frontend-test

integration-test:
	cd $(BACKEND_DIR) && source .venv/bin/activate && pytest -q tests -m integration

smoke-test:
	cd $(BACKEND_DIR) && source .venv/bin/activate && pytest -q tests/test_smoke.py

lint:
	cd $(BACKEND_DIR) && source .venv/bin/activate && ruff check .
	cd $(FRONTEND_DIR) && npm run lint

format:
	cd $(BACKEND_DIR) && source .venv/bin/activate && ruff format .
	cd $(FRONTEND_DIR) && npm run format

alembic-upgrade:
	cd $(BACKEND_DIR) && source .venv/bin/activate && alembic upgrade head

alembic-revision:
	cd $(BACKEND_DIR) && source .venv/bin/activate && alembic revision --autogenerate -m "$(m)"
