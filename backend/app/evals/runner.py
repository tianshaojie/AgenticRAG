from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.executor import FiniteStateAgentExecutor
from app.agent.policy import DefaultAgentPolicy
from app.agent.rewrite import DefaultQueryRewriteStrategy
from app.core.config import Settings
from app.db.models import AgentTrace, Document, DocumentChunk, EvalCase, EvalResult, EvalRun
from app.domain.enums import DocumentStatus, EvalRunStatus
from app.domain.interfaces import EvaluationRunner, ScoredChunk
from app.evals.dataset import GoldenCaseSpec, GoldenDataset, load_golden_dataset
from app.indexing.chunker import SlidingWindowChunker
from app.indexing.embedder import DeterministicEmbedder
from app.indexing.pgvector_index import PgVectorIndex
from app.indexing.service import DocumentIndexingService
from app.ingestion.service import SimpleDocumentIngestionService
from app.retrieval.repository import RetrievalRepository
from app.retrieval.reranker_factory import build_reranker
from app.retrieval.service import PgVectorRetriever
from app.services.answer_factory import build_answer_generator
from app.services.citation import BasicCitationAssembler
from app.services.rag_chat import RAGChatService


@dataclass(slots=True)
class CaseExecution:
    case: EvalCase
    passed: bool
    score: float
    metrics: dict[str, Any]
    output_answer: str
    output_citations: list[dict[str, Any]]
    trace_id: UUID | None


class PgEvaluationRunner(EvaluationRunner):
    def __init__(self, *, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._logger = logging.getLogger("app.evals")

    def _build_chat_service(self) -> RAGChatService:
        embedder = DeterministicEmbedder(dimension=self._settings.vector_dim)
        vector_index = PgVectorIndex(db=self._db, settings=self._settings)
        repository = RetrievalRepository(vector_index=vector_index, db=self._db)
        retriever = PgVectorRetriever(embedder=embedder, repository=repository, settings=self._settings)
        reranker = build_reranker(settings=self._settings)
        citation_assembler = BasicCitationAssembler()
        answer_generator = build_answer_generator(settings=self._settings)
        executor = FiniteStateAgentExecutor(
            db=self._db,
            settings=self._settings,
            retriever=retriever,
            reranker=reranker,
            citation_assembler=citation_assembler,
            answer_generator=answer_generator,
            policy=DefaultAgentPolicy(),
            rewrite_strategy=DefaultQueryRewriteStrategy(),
        )
        return RAGChatService(db=self._db, agent_executor=executor)

    async def _ensure_dataset_documents(self, dataset: GoldenDataset) -> dict[str, UUID]:
        ingestion = SimpleDocumentIngestionService(self._db)
        indexing = DocumentIndexingService(
            db=self._db,
            chunker=SlidingWindowChunker(
                chunk_size=self._settings.default_chunk_size,
                chunk_overlap=self._settings.default_chunk_overlap,
            ),
            embedder=DeterministicEmbedder(dimension=self._settings.vector_dim),
            vector_index=PgVectorIndex(db=self._db, settings=self._settings),
            settings=self._settings,
        )

        doc_key_to_id: dict[str, UUID] = {}
        for spec in dataset.documents:
            external_id = f"eval:{dataset.name}:{spec.key}"
            existing = self._db.execute(
                select(Document).where(Document.external_id == external_id)
            ).scalar_one_or_none()

            content_bytes = spec.content.encode("utf-8")
            content_hash = hashlib.sha256(content_bytes).hexdigest()

            if existing is None:
                created = ingestion.create_document(
                    title=spec.title,
                    filename=f"{spec.key}.txt",
                    mime_type=spec.mime_type,
                    content_bytes=content_bytes,
                    metadata={"eval_dataset": dataset.name, "eval_doc_key": spec.key},
                    request_id=f"eval-doc-{spec.key}",
                    trace_id=f"eval-doc-{spec.key}",
                )
                created.external_id = external_id
                self._db.commit()
                self._db.refresh(created)
                existing = created

            doc_key_to_id[spec.key] = existing.id

            latest_hash = self._db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == existing.id)
                .order_by(DocumentChunk.chunk_index.asc())
                .limit(1)
            ).scalar_one_or_none()

            needs_reindex = existing.status != DocumentStatus.INDEXED or latest_hash is None
            if needs_reindex:
                await indexing.index_document(
                    document_id=existing.id,
                    embedding_model=self._settings.default_embedding_model,
                    request_id=f"eval-index-{spec.key}",
                    timeout_seconds=self._settings.embedding_timeout_seconds,
                    trace_id=f"eval-index-{spec.key}",
                )

            # Refresh hash marker when document was manually changed outside ingestion/indexing path.
            existing.meta = {
                **(existing.meta or {}),
                "eval_dataset": dataset.name,
                "eval_doc_key": spec.key,
                "content_sha256": content_hash,
            }
            self._db.flush()

        self._db.commit()
        return doc_key_to_id

    def _upsert_eval_case(self, *, dataset: GoldenDataset, case: GoldenCaseSpec) -> EvalCase:
        row = self._db.execute(
            select(EvalCase)
            .where(EvalCase.dataset == dataset.name)
            .where(EvalCase.name == case.name)
            .limit(1)
        ).scalar_one_or_none()

        values = {
            "input_query": case.question,
            "expected_answer": None,
            "expected_citations": [],
            "expected_document_keys": case.expected_document_keys,
            "expected_chunk_indices": case.expected_chunk_indices,
            "expected_abstain": case.expected_abstain,
            "citation_constraints": case.citation_constraints,
            "tags": case.tags,
            "difficulty": case.difficulty,
            "scenario_type": case.scenario_type,
            "meta": {
                "source": "golden_dataset",
                "dataset": dataset.name,
            },
        }

        if row is None:
            row = EvalCase(
                id=uuid.uuid4(),
                name=case.name,
                dataset=dataset.name,
                **values,
            )
            self._db.add(row)
            self._db.flush()
            return row

        for key, value in values.items():
            setattr(row, key, value)
        self._db.flush()
        return row

    def _expected_chunk_ids(self, *, doc_key_to_id: dict[str, UUID], case: GoldenCaseSpec) -> set[UUID]:
        if not case.expected_document_keys:
            return set()

        if case.expected_chunk_indices:
            rows = self._db.execute(
                select(DocumentChunk.id)
                .where(DocumentChunk.document_id.in_([doc_key_to_id[key] for key in case.expected_document_keys]))
                .where(DocumentChunk.chunk_index.in_(case.expected_chunk_indices))
            ).all()
            return {row[0] for row in rows}

        rows = self._db.execute(
            select(DocumentChunk.id).where(
                DocumentChunk.document_id.in_([doc_key_to_id[key] for key in case.expected_document_keys])
            )
        ).all()
        return {row[0] for row in rows}

    def _retrieval_metrics(
        self,
        *,
        ranked: list[ScoredChunk],
        expected_doc_ids: set[UUID],
        expected_chunk_ids: set[UUID],
    ) -> dict[str, float]:
        ranked_chunk_ids = [item.chunk.chunk_id for item in ranked]
        ranked_doc_ids = [item.chunk.document_id for item in ranked]

        doc_hit_rank: int | None = None
        for idx, document_id in enumerate(ranked_doc_ids, start=1):
            if document_id in expected_doc_ids:
                doc_hit_rank = idx
                break

        chunk_hit_rank: int | None = None
        for idx, chunk_id in enumerate(ranked_chunk_ids, start=1):
            if chunk_id in expected_chunk_ids:
                chunk_hit_rank = idx
                break

        if expected_chunk_ids:
            matched_chunks = len(set(ranked_chunk_ids) & expected_chunk_ids)
            recall_at_k = matched_chunks / max(len(expected_chunk_ids), 1)
            hit_rate_at_k = 1.0 if chunk_hit_rank else 0.0
            mrr = 1.0 / chunk_hit_rank if chunk_hit_rank else 0.0
        elif expected_doc_ids:
            matched_docs = len(set(ranked_doc_ids) & expected_doc_ids)
            recall_at_k = matched_docs / max(len(expected_doc_ids), 1)
            hit_rate_at_k = 1.0 if doc_hit_rank else 0.0
            mrr = 1.0 / doc_hit_rank if doc_hit_rank else 0.0
        else:
            recall_at_k = 1.0
            hit_rate_at_k = 1.0
            mrr = 1.0

        return {
            "recall_at_k": recall_at_k,
            "hit_rate_at_k": hit_rate_at_k,
            "mrr": mrr,
        }

    def _citation_integrity(
        self,
        *,
        citations: list[dict[str, Any]],
        expected_doc_ids: set[UUID],
        require_expected_document: bool,
    ) -> dict[str, Any]:
        if not citations:
            return {
                "citation_present": False,
                "citation_parseable": True,
                "citation_resolved": True,
                "citation_document_match": not require_expected_document,
                "citation_integrity_failures": [],
            }

        failures: list[str] = []
        chunk_ids: list[UUID] = []
        parseable = True
        for citation in citations:
            try:
                chunk_id = UUID(str(citation["chunk_id"]))
                document_id = UUID(str(citation["document_id"]))
                start_char = int(citation["start_char"])
                end_char = int(citation["end_char"])
                if start_char < 0 or end_char <= start_char:
                    raise ValueError("invalid span")
                _ = document_id
                chunk_ids.append(chunk_id)
            except Exception:
                parseable = False
                failures.append("citation_unparseable")

        if not parseable:
            return {
                "citation_present": True,
                "citation_parseable": False,
                "citation_resolved": False,
                "citation_document_match": False,
                "citation_integrity_failures": failures,
            }

        rows = self._db.execute(select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))).scalars().all()
        by_id = {row.id: row for row in rows}

        resolved = True
        document_match = True
        for citation in citations:
            chunk_id = UUID(str(citation["chunk_id"]))
            document_id = UUID(str(citation["document_id"]))
            start_char = int(citation["start_char"])
            end_char = int(citation["end_char"])

            row = by_id.get(chunk_id)
            if row is None:
                resolved = False
                failures.append("citation_chunk_missing")
                continue
            if row.document_id != document_id:
                resolved = False
                failures.append("citation_document_mismatch")
            if end_char > len(row.content) or start_char < 0 or end_char <= start_char:
                resolved = False
                failures.append("citation_span_out_of_range")
            if require_expected_document and expected_doc_ids and row.document_id not in expected_doc_ids:
                document_match = False
                failures.append("citation_not_in_expected_document")

        return {
            "citation_present": True,
            "citation_parseable": True,
            "citation_resolved": resolved,
            "citation_document_match": document_match,
            "citation_integrity_failures": sorted(set(failures)),
        }

    async def _run_case(
        self,
        *,
        case_row: EvalCase,
        case_spec: GoldenCaseSpec,
        chat_service: RAGChatService,
        doc_key_to_id: dict[str, UUID],
        run_id: UUID,
    ) -> CaseExecution:
        top_k = case_spec.top_k or int(self._settings.default_top_k)
        score_threshold = (
            case_spec.score_threshold
            if case_spec.score_threshold is not None
            else float(self._settings.default_score_threshold)
        )

        request_id = f"eval-{run_id.hex[:12]}-{case_row.id.hex[:12]}"
        trace_request_id = f"trace-{run_id.hex[:12]}-{case_row.id.hex[:12]}"

        session, message, ranked, answer, trace_db_id = await chat_service.ask(
            session_id=None,
            query=case_spec.question,
            top_k=top_k,
            score_threshold=score_threshold,
            embedding_model=self._settings.default_embedding_model,
            request_id=request_id,
            trace_id=trace_request_id,
        )
        _ = session

        expected_doc_ids = {doc_key_to_id[key] for key in case_spec.expected_document_keys if key in doc_key_to_id}
        expected_chunk_ids = self._expected_chunk_ids(doc_key_to_id=doc_key_to_id, case=case_spec)

        retrieval = self._retrieval_metrics(
            ranked=ranked,
            expected_doc_ids=expected_doc_ids,
            expected_chunk_ids=expected_chunk_ids,
        )

        citations = [
            {
                "chunk_id": str(citation.chunk_id),
                "document_id": str(citation.document_id),
                "quote": citation.quote,
                "score": float(citation.score),
                "start_char": citation.start_char,
                "end_char": citation.end_char,
            }
            for citation in answer.citations
        ]

        constraints = dict(case_spec.citation_constraints or {})
        min_count = int(constraints.get("min_count", 0 if case_spec.expected_abstain else 1))
        require_resolved_chunk = bool(constraints.get("require_resolved_chunk", True))
        require_expected_document = bool(constraints.get("require_expected_document", False))

        citation_integrity = self._citation_integrity(
            citations=citations,
            expected_doc_ids=expected_doc_ids,
            require_expected_document=require_expected_document,
        )

        trace = self._db.get(AgentTrace, trace_db_id)
        step_count = len(trace.steps) if trace is not None else 0
        rewrite_count = int((trace.meta or {}).get("rewrite_count", 0)) if trace is not None else 0
        fallback_used = bool((trace.meta or {}).get("fallback_used", False)) if trace is not None else False
        fallback_visible = False
        if trace is not None:
            fallback_visible = any(bool((step.output_payload or {}).get("fallback", False)) for step in trace.steps)

        failure_reasons: list[str] = []

        if answer.abstained != case_spec.expected_abstain:
            failure_reasons.append("abstain_expectation_mismatch")

        if case_spec.expected_document_keys and retrieval["hit_rate_at_k"] < 1.0:
            failure_reasons.append("retrieval_expected_hit_missed")

        if not case_spec.expected_abstain and len(citations) < min_count:
            failure_reasons.append("citation_count_below_min")

        if not citation_integrity["citation_parseable"]:
            failure_reasons.append("citation_unparseable")

        if require_resolved_chunk and not citation_integrity["citation_resolved"]:
            failure_reasons.append("citation_unresolved")

        if require_expected_document and not citation_integrity["citation_document_match"]:
            failure_reasons.append("citation_expected_document_mismatch")

        unsupported_answer = (not answer.abstained) and len(citations) == 0
        if unsupported_answer:
            failure_reasons.append("answered_without_citation")

        if step_count > self._settings.agent_max_steps:
            failure_reasons.append("agent_step_limit_exceeded")

        if rewrite_count > self._settings.agent_max_rewrites:
            failure_reasons.append("agent_rewrite_limit_exceeded")

        if fallback_used and not fallback_visible:
            failure_reasons.append("fallback_not_visible_in_trace")

        passed = len(failure_reasons) == 0

        checks = 10
        score = max(0.0, (checks - len(set(failure_reasons))) / checks)

        metrics = {
            "dataset": case_row.dataset,
            "case_name": case_row.name,
            "query": case_row.input_query,
            "expected_abstain": case_spec.expected_abstain,
            "actual_abstained": answer.abstained,
            "retrieval": retrieval,
            "answer": {
                "answered": not answer.abstained,
                "unsupported_answer": unsupported_answer,
                "citation_count": len(citations),
            },
            "citation": citation_integrity,
            "agent": {
                "step_count": step_count,
                "rewrite_count": rewrite_count,
                "fallback_used": fallback_used,
                "fallback_visible": fallback_visible,
                "max_steps": self._settings.agent_max_steps,
                "max_rewrites": self._settings.agent_max_rewrites,
            },
            "failure_reasons": sorted(set(failure_reasons)),
            "top_k": top_k,
            "score_threshold": score_threshold,
        }

        return CaseExecution(
            case=case_row,
            passed=passed,
            score=score,
            metrics=metrics,
            output_answer=message.content,
            output_citations=message.citations,
            trace_id=trace_db_id,
        )

    def _build_summary(self, *, executions: list[CaseExecution], dataset_name: str) -> dict[str, Any]:
        total = len(executions)
        passed = sum(1 for item in executions if item.passed)
        failed = total - passed

        def _avg(path: tuple[str, ...]) -> float:
            values: list[float] = []
            for item in executions:
                node: Any = item.metrics
                for key in path:
                    node = node.get(key, {}) if isinstance(node, dict) else {}
                if isinstance(node, (int, float)):
                    values.append(float(node))
            return sum(values) / len(values) if values else 0.0

        unsupported_count = sum(
            1 for item in executions if bool(item.metrics.get("answer", {}).get("unsupported_answer", False))
        )
        citation_integrity_failures = sum(
            1
            for item in executions
            if len(item.metrics.get("citation", {}).get("citation_integrity_failures", [])) > 0
        )
        step_violations = sum(
            1
            for item in executions
            if "agent_step_limit_exceeded" in item.metrics.get("failure_reasons", [])
        )
        rewrite_violations = sum(
            1
            for item in executions
            if "agent_rewrite_limit_exceeded" in item.metrics.get("failure_reasons", [])
        )
        fallback_visibility_failures = sum(
            1
            for item in executions
            if "fallback_not_visible_in_trace" in item.metrics.get("failure_reasons", [])
        )

        unsupported_answer_rate = unsupported_count / total if total else 0.0
        gate_passed = (
            failed == 0
            and unsupported_answer_rate <= self._settings.eval_max_unsupported_answer_rate
            and citation_integrity_failures == 0
            and step_violations == 0
            and rewrite_violations == 0
            and fallback_visibility_failures == 0
        )

        failed_cases = [
            {
                "case_id": str(item.case.id),
                "case_name": item.case.name,
                "query": item.case.input_query,
                "reasons": item.metrics.get("failure_reasons", []),
            }
            for item in executions
            if not item.passed
        ]

        return {
            "dataset": dataset_name,
            "total_cases": total,
            "passed_cases": passed,
            "failed_cases": failed,
            "pass_rate": (passed / total) if total else 0.0,
            "retrieval": {
                "recall_at_k": _avg(("retrieval", "recall_at_k")),
                "hit_rate_at_k": _avg(("retrieval", "hit_rate_at_k")),
                "mrr": _avg(("retrieval", "mrr")),
            },
            "answer": {
                "answer_rate": _avg(("answer", "answered")),
                "abstain_rate": 1.0 - _avg(("answer", "answered")),
                "unsupported_answer_rate": unsupported_answer_rate,
                "unsupported_answer_rate_threshold": self._settings.eval_max_unsupported_answer_rate,
                "unsupported_answer_rate_warning_threshold": self._settings.eval_warning_unsupported_answer_rate,
                "citation_presence_rate": _avg(("citation", "citation_present")),
                "citation_parseable_rate": _avg(("citation", "citation_parseable")),
                "citation_resolved_rate": _avg(("citation", "citation_resolved")),
                "citation_integrity_failures": citation_integrity_failures,
            },
            "agent": {
                "step_limit_violations": step_violations,
                "rewrite_limit_violations": rewrite_violations,
                "fallback_visibility_failures": fallback_visibility_failures,
            },
            "failed_case_samples": failed_cases,
            "gate_passed": gate_passed,
        }

    async def run(self, *, run_id: UUID) -> None:
        run = self._db.get(EvalRun, run_id)
        if run is None:
            raise ValueError("eval_run_not_found")

        dataset_name = str((run.config or {}).get("dataset", self._settings.eval_default_dataset))
        run.status = EvalRunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        run.summary = {}
        self._db.flush()

        try:
            dataset_path = (run.config or {}).get("dataset_path")
            dataset = load_golden_dataset(
                dataset=dataset_name,
                dataset_dir=self._settings.eval_dataset_dir,
                dataset_path=dataset_path,
            )
            doc_key_to_id = await self._ensure_dataset_documents(dataset)

            self._db.query(EvalResult).filter(EvalResult.run_id == run.id).delete(synchronize_session=False)
            self._db.flush()

            chat_service = self._build_chat_service()
            executions: list[CaseExecution] = []
            for case_spec in dataset.cases:
                case_row = self._upsert_eval_case(dataset=dataset, case=case_spec)
                execution = await self._run_case(
                    case_row=case_row,
                    case_spec=case_spec,
                    chat_service=chat_service,
                    doc_key_to_id=doc_key_to_id,
                    run_id=run.id,
                )
                executions.append(execution)

                self._db.add(
                    EvalResult(
                        id=uuid.uuid4(),
                        run_id=run.id,
                        case_id=case_row.id,
                        trace_id=execution.trace_id,
                        score=Decimal(f"{execution.score:.4f}"),
                        passed=execution.passed,
                        metrics=execution.metrics,
                        output_answer=execution.output_answer,
                        output_citations=execution.output_citations,
                        error_message=None,
                    )
                )
                self._db.flush()

            summary = self._build_summary(executions=executions, dataset_name=dataset.name)
            run.summary = summary
            run.status = EvalRunStatus.SUCCEEDED if summary.get("gate_passed", False) else EvalRunStatus.FAILED
            run.finished_at = datetime.now(UTC)
            self._db.commit()

            self._logger.info(
                "eval_run_completed",
                extra={
                    "eval_run_id": str(run.id),
                    "status": run.status.value,
                    "dataset": dataset.name,
                    "request_id": f"eval-{run.id}",
                    "trace_id": str(run.id),
                    "fallback_used": False,
                },
            )
        except Exception as exc:
            self._db.rollback()
            run = self._db.get(EvalRun, run_id)
            if run is None:
                raise
            run.status = EvalRunStatus.FAILED
            run.finished_at = datetime.now(UTC)
            run.summary = {
                "dataset": dataset_name,
                "gate_passed": False,
                "error": str(exc),
            }
            self._db.commit()
            raise
