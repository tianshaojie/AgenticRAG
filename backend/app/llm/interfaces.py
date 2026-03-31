from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


LLMRole = Literal["system", "user", "assistant"]


@dataclass(slots=True)
class LLMMessage:
    role: LLMRole
    content: str


@dataclass(slots=True)
class LLMCompletionRequest:
    messages: list[LLMMessage]
    model: str
    temperature: float | None = None
    max_tokens: int | None = None
    timeout_seconds: float | None = None
    request_id: str = "unknown"
    trace_id: str = "unknown"


@dataclass(slots=True)
class LLMCompletionResponse:
    text: str
    model: str | None = None
    finish_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    async def chat_completion(self, *, request: LLMCompletionRequest) -> LLMCompletionResponse:
        """Generate assistant text from provider-neutral chat completion request."""
