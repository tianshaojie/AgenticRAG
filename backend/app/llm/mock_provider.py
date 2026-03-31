from __future__ import annotations

from app.llm.interfaces import LLMCompletionRequest, LLMCompletionResponse, LLMProvider


class MockLLMProvider(LLMProvider):
    """Deterministic local provider for tests and offline flows."""

    async def chat_completion(self, *, request: LLMCompletionRequest) -> LLMCompletionResponse:
        evidence_lines: list[str] = []
        for message in request.messages:
            if message.role != "user":
                continue
            for raw_line in message.content.splitlines():
                line = raw_line.strip()
                if line.startswith("- "):
                    evidence_lines.append(line)

        if evidence_lines:
            text = "Based on the retrieved evidence:\n" + "\n".join(evidence_lines[:2])
        else:
            text = "Insufficient evidence to answer reliably."

        return LLMCompletionResponse(
            text=text,
            model="mock-llm-v1",
            finish_reason="stop",
            metadata={"provider": "mock"},
        )
