from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.agent.executor import FiniteStateAgentExecutor
from app.db.models import AgentTrace, ChatMessage, ChatSession
from app.domain.enums import MessageRole
from app.domain.interfaces import GeneratedAnswer, ScoredChunk
from app.observability.metrics import metrics


class RAGChatService:
    def __init__(
        self,
        *,
        db: Session,
        agent_executor: FiniteStateAgentExecutor,
    ) -> None:
        self._db = db
        self._agent_executor = agent_executor
        self._logger = logging.getLogger("app.chat")

    async def ask(
        self,
        *,
        session_id,
        query: str,
        top_k: int,
        score_threshold: float,
        embedding_model: str,
        request_id: str,
        trace_id: str,
    ) -> tuple[ChatSession, ChatMessage, list[ScoredChunk], GeneratedAnswer, UUID]:
        if session_id is None:
            session = ChatSession(id=uuid.uuid4(), title=query[:64], meta={})
            self._db.add(session)
            self._db.flush()
        else:
            session = self._db.get(ChatSession, session_id)
            if session is None:
                raise ValueError("chat_session_not_found")

        user_message = ChatMessage(
            id=uuid.uuid4(),
            session_id=session.id,
            role=MessageRole.USER,
            content=query,
            abstained=False,
            citations=[],
            meta={"request_id": request_id},
        )
        self._db.add(user_message)
        self._db.flush()

        execution = await self._agent_executor.run(
            session_id=session.id,
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            embedding_model=embedding_model,
            request_id=request_id,
            trace_id=trace_id,
        )

        assistant_message = ChatMessage(
            id=uuid.uuid4(),
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=execution.answer.text,
            abstained=execution.answer.abstained,
            citations=[
                {
                    "chunk_id": str(c.chunk_id),
                    "document_id": str(c.document_id),
                    "quote": c.quote,
                    "score": c.score,
                    "start_char": c.start_char,
                    "end_char": c.end_char,
                }
                for c in execution.answer.citations
            ],
            meta={"request_id": request_id, "reason": execution.answer.reason},
            created_at=datetime.now(UTC),
        )
        self._db.add(assistant_message)
        self._db.flush()

        trace = self._db.get(AgentTrace, execution.trace_db_id)
        if trace is not None:
            trace.assistant_message_id = assistant_message.id

        self._db.commit()

        self._logger.info(
            "chat_query_processed",
            extra={
                "request_id": request_id,
                "trace_id": str(execution.trace_db_id),
                "query_id": str(user_message.id),
                "session_id": str(session.id),
                "retrieved_count": len(execution.ranked_chunks),
                "abstained": execution.answer.abstained,
                "fallback_used": bool(trace.meta.get("fallback_used")) if trace else False,
            },
        )
        metrics.record_abstain(abstained=execution.answer.abstained)
        metrics.record_fallback(used=bool(trace.meta.get("fallback_used")) if trace else False)
        return session, assistant_message, execution.ranked_chunks, execution.answer, execution.trace_db_id
