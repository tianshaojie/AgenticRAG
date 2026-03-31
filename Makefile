SHELL := /bin/zsh

BACKEND_DIR := backend
FRONTEND_DIR := frontend
LOCAL_PG_HOST ?= 127.0.0.1
LOCAL_PG_PORT ?= 5432
LOCAL_PG_USER ?= $(shell whoami)
RAG_DATABASE_URL ?= postgresql+psycopg://$(LOCAL_PG_USER)@$(LOCAL_PG_HOST):$(LOCAL_PG_PORT)/agentic_rag_dev
RAG_TEST_DATABASE_URL ?= postgresql+psycopg://$(LOCAL_PG_USER)@$(LOCAL_PG_HOST):$(LOCAL_PG_PORT)/agentic_rag_test

.PHONY: backend-install frontend-install install backend-dev frontend-dev dev backend-test frontend-test test integration-test eval smoke smoke-test lint format db-init db-setup migrate alembic-upgrade alembic-revision backend-build frontend-build build

export RAG_DATABASE_URL
export RAG_TEST_DATABASE_URL

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
	@./scripts/dev.sh

backend-test:
	cd $(BACKEND_DIR) && source .venv/bin/activate && pytest -q

frontend-test:
	cd $(FRONTEND_DIR) && npm run test

test: backend-test frontend-test

integration-test:
	cd $(BACKEND_DIR) && source .venv/bin/activate && pytest -q tests -m integration

eval:
	cd $(BACKEND_DIR) && source .venv/bin/activate && python -m app.evals.cli --dataset golden_v1 --name local-eval

smoke: smoke-test

smoke-test:
	cd $(BACKEND_DIR) && source .venv/bin/activate && pytest -q tests/test_smoke.py

lint:
	cd $(BACKEND_DIR) && source .venv/bin/activate && ruff check . --select F,E9
	cd $(FRONTEND_DIR) && npm run lint

format:
	cd $(BACKEND_DIR) && source .venv/bin/activate && ruff format .
	cd $(FRONTEND_DIR) && npm run format

db-init:
	@./scripts/db-init.sh

db-setup: db-init migrate

migrate: alembic-upgrade

alembic-upgrade:
	cd $(BACKEND_DIR) && source .venv/bin/activate && alembic upgrade head

alembic-revision:
	cd $(BACKEND_DIR) && source .venv/bin/activate && alembic revision --autogenerate -m "$(m)"

backend-build:
	cd $(BACKEND_DIR) && source .venv/bin/activate && python -m compileall -q app

frontend-build:
	cd $(FRONTEND_DIR) && npm run build

build: backend-build frontend-build
