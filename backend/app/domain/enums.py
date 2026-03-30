from enum import Enum


class DocumentStatus(str, Enum):
    RECEIVED = "received"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class TraceStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    ABSTAINED = "abstained"
    FAILED = "failed"


class StepStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class EvalRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
