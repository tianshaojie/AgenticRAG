from __future__ import annotations

import argparse
import asyncio
import json
import uuid

from app.core.config import get_settings
from app.db import session as db_session_module
from app.db.models import EvalRun
from app.domain.enums import EvalRunStatus
from app.evals.runner import PgEvaluationRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run eval/regression gate for Agentic RAG")
    parser.add_argument("--dataset", default=None, help="Dataset name under eval dataset directory")
    parser.add_argument("--dataset-path", default=None, help="Absolute or relative path to dataset json")
    parser.add_argument("--name", default="ci-eval-run", help="Eval run name")
    parser.add_argument("--triggered-by", default="cli", help="Triggered by")
    return parser


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    db_session_module.init_engine(settings.database_url)
    assert db_session_module.SessionLocal is not None

    with db_session_module.SessionLocal() as db:
        run = EvalRun(
            id=uuid.uuid4(),
            name=args.name,
            status=EvalRunStatus.QUEUED,
            triggered_by=args.triggered_by,
            config={
                "dataset": args.dataset or settings.eval_default_dataset,
                "dataset_path": args.dataset_path,
            },
            summary={},
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        runner = PgEvaluationRunner(db=db, settings=settings)
        await runner.run(run_id=run.id)

        db.refresh(run)
        output = {
            "eval_run_id": str(run.id),
            "status": run.status.value if hasattr(run.status, "value") else str(run.status),
            "summary": run.summary,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))

        gate_passed = bool((run.summary or {}).get("gate_passed", False))
        if run.status != EvalRunStatus.SUCCEEDED or not gate_passed:
            return 1

    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    code = asyncio.run(_run(args))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
