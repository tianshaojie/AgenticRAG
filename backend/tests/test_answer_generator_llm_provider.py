from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.errors import DependencyAppError
from app.domain.interfaces import CitationRecord
from app.llm.interfaces import LLMCompletionRequest, LLMCompletionResponse, LLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.services.answer import ThresholdAnswerGenerator


def _citation(score: float = 0.9) -> CitationRecord:
    return CitationRecord(
        chunk_id=uuid4(),
        document_id=uuid4(),
        quote="信用账户可以用于融资买入和融券卖出。",
        score=score,
        start_char=0,
        end_char=18,
    )


class SpyLLMProvider(LLMProvider):
    def __init__(self) -> None:
        self.called = False

    async def chat_completion(self, *, request: LLMCompletionRequest) -> LLMCompletionResponse:
        self.called = True
        return LLMCompletionResponse(text="ok")


class FailingLLMProvider(LLMProvider):
    async def chat_completion(self, *, request: LLMCompletionRequest) -> LLMCompletionResponse:
        _ = request
        raise DependencyAppError(code="llm_provider_unavailable", message="upstream down")


@pytest.mark.asyncio
async def test_answer_generator_uses_mock_llm_provider() -> None:
    generator = ThresholdAnswerGenerator(
        min_citations=1,
        min_score=0.5,
        llm_provider=MockLLMProvider(),
        llm_model="mock-llm-v1",
    )

    result = await generator.generate(query="信用账户", citations=[_citation()])

    assert result.abstained is False
    assert "Based on the retrieved evidence" in result.text
    assert len(result.citations) == 1


@pytest.mark.asyncio
async def test_answer_generator_abstains_before_calling_llm_provider() -> None:
    spy_provider = SpyLLMProvider()
    generator = ThresholdAnswerGenerator(
        min_citations=2,
        min_score=0.5,
        llm_provider=spy_provider,
        llm_model="mock-llm-v1",
    )

    result = await generator.generate(query="信用账户", citations=[_citation()])

    assert result.abstained is True
    assert result.reason == "insufficient_citation_count"
    assert spy_provider.called is False


@pytest.mark.asyncio
async def test_answer_generator_propagates_provider_errors() -> None:
    generator = ThresholdAnswerGenerator(
        min_citations=1,
        min_score=0.5,
        llm_provider=FailingLLMProvider(),
        llm_model="demo-model",
    )

    with pytest.raises(DependencyAppError) as exc_info:
        await generator.generate(query="信用账户", citations=[_citation()])

    assert exc_info.value.code == "llm_provider_unavailable"
