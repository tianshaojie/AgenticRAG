from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.deps import get_db
from app.core.config import get_settings
from app.db import session as db_session_module


def _find_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_db(url: str, timeout_seconds: int = 60) -> None:
    import sqlalchemy as sa

    start = time.time()
    last_error = ""
    while time.time() - start < timeout_seconds:
        try:
            engine = sa.create_engine(url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # pragma: no cover - helper
            last_error = str(exc)
            time.sleep(1)
    raise RuntimeError(f"Database not ready: {last_error}")


@pytest.fixture(scope="session")
def integration_db_url() -> str:
    direct_url = os.getenv("RAG_TEST_DATABASE_URL")
    if direct_url:
        os.environ["RAG_DATABASE_URL"] = direct_url
        get_settings.cache_clear()

        backend_dir = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["RAG_DATABASE_URL"] = direct_url
        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            env=env,
            check=True,
        )
        return direct_url

    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        pytest.skip("docker not available for integration tests")

    port = _find_free_port()
    container_name = f"agenticrag-pg-{port}"
    image = os.getenv("RAG_PGVECTOR_IMAGE", "pgvector/pgvector:pg16")

    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-d",
            "--name",
            container_name,
            "-e",
            "POSTGRES_USER=postgres",
            "-e",
            "POSTGRES_PASSWORD=postgres",
            "-e",
            "POSTGRES_DB=agentic_rag_test",
            "-p",
            f"{port}:5432",
            image,
        ],
        check=True,
    )

    db_url = f"postgresql+psycopg://postgres:postgres@127.0.0.1:{port}/agentic_rag_test"

    try:
        _wait_for_db(db_url)

        backend_dir = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["RAG_DATABASE_URL"] = db_url
        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            env=env,
            check=True,
        )

        os.environ["RAG_DATABASE_URL"] = db_url
        get_settings.cache_clear()
        yield db_url
    finally:
        subprocess.run(["docker", "rm", "-f", container_name], check=False)


@pytest.fixture()
def db_session(integration_db_url: str):
    os.environ["RAG_DATABASE_URL"] = integration_db_url
    get_settings.cache_clear()
    db_session_module.init_engine(integration_db_url)
    assert db_session_module.SessionLocal is not None

    session = db_session_module.SessionLocal()
    session.execute(
        text(
            """
            TRUNCATE TABLE
                eval_results,
                eval_runs,
                eval_cases,
                agent_trace_steps,
                agent_traces,
                chat_messages,
                chat_sessions,
                chunk_vectors,
                document_chunks,
                document_versions,
                documents
            RESTART IDENTITY CASCADE
            """
        )
    )
    session.commit()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    from app.main import app

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
