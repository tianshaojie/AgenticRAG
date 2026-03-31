from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import EvalResult, EvalRun
from app.domain.enums import EvalRunStatus
from app.evals.runner import PgEvaluationRunner


@pytest.mark.integration
@pytest.mark.asyncio
async def test_eval_runner_persists_summary_and_results(db_session) -> None:
    settings = get_settings()
    run = EvalRun(
        id=uuid.uuid4(),
        name="test-eval",
        status=EvalRunStatus.QUEUED,
        triggered_by="pytest",
        config={"dataset": settings.eval_default_dataset},
        summary={},
    )
    db_session.add(run)
    db_session.commit()

    runner = PgEvaluationRunner(db=db_session, settings=settings)
    await runner.run(run_id=run.id)

    db_session.refresh(run)
    assert run.status == EvalRunStatus.SUCCEEDED
    assert run.summary["gate_passed"] is True
    assert "retrieval" in run.summary
    assert "answer" in run.summary
    assert "agent" in run.summary

    rows = db_session.execute(select(EvalResult).where(EvalResult.run_id == run.id)).scalars().all()
    assert len(rows) == run.summary["total_cases"]
    assert all("retrieval" in row.metrics for row in rows)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_eval_runner_fails_gate_on_citation_integrity(tmp_path, db_session) -> None:
    dataset_path = tmp_path / "citation_mismatch.json"
    dataset_path.write_text(
        json.dumps(
            {
                "dataset": "citation_mismatch",
                "documents": [
                    {
                        "key": "doc_hit",
                        "title": "Doc Hit",
                        "content": "alpha token should be found",
                    },
                    {
                        "key": "doc_expected",
                        "title": "Doc Expected",
                        "content": "unrelated content only",
                    },
                ],
                "cases": [
                    {
                        "name": "mismatch_case",
                        "question": "alpha token should be found",
                        "expected_document_keys": ["doc_expected"],
                        "expected_chunk_indices": [0],
                        "expected_abstain": False,
                        "citation_constraints": {
                            "min_count": 1,
                            "require_resolved_chunk": True,
                            "require_expected_document": True,
                        },
                        "tags": ["citation", "mismatch"],
                        "difficulty": "easy",
                        "scenario_type": "single_hop",
                        "top_k": 5,
                        "score_threshold": 0.1,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    settings = get_settings()
    run = EvalRun(
        id=uuid.uuid4(),
        name="test-eval-citation-mismatch",
        status=EvalRunStatus.QUEUED,
        triggered_by="pytest",
        config={
            "dataset": "citation_mismatch",
            "dataset_path": str(dataset_path),
        },
        summary={},
    )
    db_session.add(run)
    db_session.commit()

    runner = PgEvaluationRunner(db=db_session, settings=settings)
    await runner.run(run_id=run.id)

    db_session.refresh(run)
    assert run.status == EvalRunStatus.FAILED
    assert run.summary["gate_passed"] is False
    assert run.summary["answer"]["citation_integrity_failures"] >= 1

    row = db_session.execute(select(EvalResult).where(EvalResult.run_id == run.id)).scalar_one()
    assert row.passed is False
    assert "citation_expected_document_mismatch" in row.metrics["failure_reasons"]
