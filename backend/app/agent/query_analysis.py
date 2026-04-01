from __future__ import annotations

import re

from app.agent.interfaces import QueryAnalyzer
from app.agent.models import QueryAnalysis


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value.strip())
    return result


class DeterministicQueryAnalyzer(QueryAnalyzer):
    """Conservative query analysis without provider dependency."""

    _TYPO_FIXES: tuple[tuple[re.Pattern[str], str, str], ...] = (
        (re.compile(r"\bretrival\b", re.IGNORECASE), "retrieval", "typo_retrival"),
        (re.compile(r"\bdocumnt\b", re.IGNORECASE), "document", "typo_documnt"),
        (re.compile(r"帐户"), "账户", "zh_variant_zhanghu"),
        (re.compile(r"賬戶"), "账户", "zh_variant_traditional"),
    )

    _EXPANSION_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
        (("信用账户", "信用帐户", "授信账户"), ("信用账户", "授信账户", "信用帐户")),
        (("slo", "service level objective", "服务等级目标"), ("SLO", "service level objective", "服务等级目标")),
        (("sla", "service level agreement", "服务等级协议"), ("SLA", "service level agreement", "服务等级协议")),
    )

    _CHITCHAT_MARKERS: tuple[str, ...] = (
        "你好",
        "您好",
        "hello",
        "hi",
        "在吗",
    )

    def _normalize(self, query: str) -> str:
        normalized = query.replace("\u3000", " ")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _apply_typos(self, normalized: str) -> tuple[str, list[str]]:
        corrected = normalized
        reasons: list[str] = []
        for pattern, replacement, reason in self._TYPO_FIXES:
            corrected, count = pattern.subn(replacement, corrected)
            if count > 0:
                reasons.append(reason)
        return corrected, reasons

    def _infer_intent(self, corrected_query: str) -> str:
        lowered = corrected_query.lower()
        if lowered.startswith("sql:"):
            return "structured_query"
        if lowered.startswith("api:"):
            return "external_lookup"
        if any(marker in lowered for marker in self._CHITCHAT_MARKERS):
            return "chitchat"
        if any(token in lowered for token in ("select ", "group by", "count(", "统计", "计数", "汇总")):
            return "structured_query"
        if any(token in lowered for token in ("api", "接口", "http://", "https://")):
            return "external_lookup"
        return "knowledge_lookup"

    def _expand_terms(self, corrected_query: str) -> list[str]:
        lowered = corrected_query.lower()
        expansions: list[str] = []
        for triggers, terms in self._EXPANSION_RULES:
            if any(trigger.lower() in lowered for trigger in triggers):
                expansions.extend(terms)
        return _dedupe_keep_order(expansions)

    def analyze(self, *, query: str, min_query_chars: int) -> QueryAnalysis:
        normalized = self._normalize(query)
        corrected, correction_reasons = self._apply_typos(normalized)
        intent = self._infer_intent(corrected)
        expanded_terms = self._expand_terms(corrected)

        reasons = list(correction_reasons)
        if len(corrected) < min_query_chars:
            need_retrieval = False
            reasons.append("query_too_short")
        elif intent == "chitchat":
            need_retrieval = False
            reasons.append("non_information_request")
        else:
            need_retrieval = True
            reasons.append("retrieval_required")

        confidence = 0.75
        if correction_reasons:
            confidence += 0.05
        if intent in {"structured_query", "external_lookup", "knowledge_lookup"}:
            confidence += 0.1
        else:
            confidence -= 0.2
        confidence = max(0.0, min(1.0, confidence))

        if not reasons:
            reasons.append("analysis_default")

        return QueryAnalysis(
            original_query=query,
            normalized_query=normalized,
            corrected_query=corrected,
            expanded_terms=expanded_terms,
            intent=intent,
            need_retrieval=need_retrieval,
            confidence=confidence,
            reasons=reasons,
        )
