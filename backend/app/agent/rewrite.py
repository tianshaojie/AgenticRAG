from __future__ import annotations

import re

from app.agent.interfaces import QueryRewriteStrategy


class DefaultQueryRewriteStrategy(QueryRewriteStrategy):
    """Conservative deterministic rewrite strategy.

    Keeps behavior predictable and bounded by rewrite count.
    """

    def rewrite(self, *, query: str, attempt: int, reason: str) -> str:
        base = re.sub(r"\s+", " ", query).strip()
        if not base:
            return query

        if attempt == 1:
            return f"{base} 定义 说明 同义词"
        if attempt == 2:
            return f"{base} 相关术语 业务含义"
        return f"{base} 详细解释"
