from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(slots=True)
class InMemoryMetrics:
    """Minimal metrics abstraction for production hardening baseline.

    This is intentionally simple and replaceable by Prometheus/OpenTelemetry exporters.
    """

    request_count: int = 0
    error_count: int = 0
    latency_observations_ms: list[float] = field(default_factory=list)
    abstain_count: int = 0
    fallback_count: int = 0
    by_path_count: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_error_code_count: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def increment_request(self, *, path: str) -> None:
        self.request_count += 1
        self.by_path_count[path] += 1

    def increment_error(self, *, path: str, category: str, code: str) -> None:
        _ = category
        self.error_count += 1
        self.by_path_count[path] += 0
        self.by_error_code_count[code] += 1

    def observe_latency(self, *, latency_ms: float) -> None:
        self.latency_observations_ms.append(latency_ms)

    def record_abstain(self, *, abstained: bool) -> None:
        if abstained:
            self.abstain_count += 1

    def record_fallback(self, *, used: bool) -> None:
        if used:
            self.fallback_count += 1

    def snapshot(self) -> dict[str, float | int | dict[str, int]]:
        total = max(self.request_count, 1)
        abstain_ratio = self.abstain_count / total
        fallback_ratio = self.fallback_count / total
        p95_latency = 0.0
        if self.latency_observations_ms:
            sorted_values = sorted(self.latency_observations_ms)
            idx = int(0.95 * (len(sorted_values) - 1))
            p95_latency = sorted_values[idx]

        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "abstain_count": self.abstain_count,
            "fallback_count": self.fallback_count,
            "abstain_ratio": round(abstain_ratio, 6),
            "fallback_ratio": round(fallback_ratio, 6),
            "latency_p95_ms": round(p95_latency, 2),
            "by_path_count": dict(self.by_path_count),
            "by_error_code_count": dict(self.by_error_code_count),
        }


metrics = InMemoryMetrics()
