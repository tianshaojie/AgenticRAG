from __future__ import annotations

from uuid import UUID

from app.domain.interfaces import EvaluationRunner


class StubEvaluationRunner(EvaluationRunner):
    async def run(self, *, run_id: UUID) -> None:
        _ = run_id
        # Step 1 scope: no execution logic yet.
        return None
