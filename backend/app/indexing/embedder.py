from __future__ import annotations

import hashlib
import math
from typing import Iterable


class DeterministicEmbedder:
    """Deterministic local embedder.

    This implementation is provider-free and replaceable via Embedder protocol.
    """

    def __init__(self, *, dimension: int) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be > 0")
        self.dimension = dimension

    def _vector_from_seed(self, seed: bytes) -> list[float]:
        out: list[float] = []
        counter = 0
        while len(out) < self.dimension:
            block = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
            for idx in range(0, len(block), 4):
                raw = int.from_bytes(block[idx : idx + 4], "big", signed=False)
                value = (raw / 4294967295.0) * 2.0 - 1.0
                out.append(value)
                if len(out) == self.dimension:
                    break
            counter += 1

        norm = math.sqrt(sum(v * v for v in out))
        if norm == 0.0:
            return out
        return [v / norm for v in out]

    async def embed(
        self,
        *,
        inputs: list[str],
        model: str,
        timeout_seconds: int | None = None,
    ) -> list[list[float]]:
        _ = timeout_seconds
        vectors: list[list[float]] = []
        for text in inputs:
            seed = hashlib.sha256(f"{model}:{text}".encode("utf-8")).digest()
            vectors.append(self._vector_from_seed(seed))
        return vectors


def vector_dimension(vectors: Iterable[list[float]]) -> int:
    first = next(iter(vectors), None)
    return len(first) if first is not None else 0
