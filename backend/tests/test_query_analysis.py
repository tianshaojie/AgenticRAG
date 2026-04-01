from __future__ import annotations

from app.agent.query_analysis import DeterministicQueryAnalyzer


def test_query_analysis_applies_typo_fix_and_keyword_expansion() -> None:
    analyzer = DeterministicQueryAnalyzer()

    result = analyzer.analyze(query="retrival 信用帐户", min_query_chars=2)

    assert result.corrected_query == "retrieval 信用账户"
    assert result.need_retrieval is True
    assert result.intent == "knowledge_lookup"
    assert "信用账户" in result.expanded_terms
    assert "typo_retrival" in result.reasons
    assert "zh_variant_zhanghu" in result.reasons


def test_query_analysis_marks_short_query_as_non_retrieval() -> None:
    analyzer = DeterministicQueryAnalyzer()

    result = analyzer.analyze(query="a", min_query_chars=2)

    assert result.need_retrieval is False
    assert "query_too_short" in result.reasons


def test_query_analysis_detects_chitchat() -> None:
    analyzer = DeterministicQueryAnalyzer()

    result = analyzer.analyze(query="你好，在吗？", min_query_chars=2)

    assert result.intent == "chitchat"
    assert result.need_retrieval is False
    assert "non_information_request" in result.reasons


def test_query_analysis_detects_structured_query_intent() -> None:
    analyzer = DeterministicQueryAnalyzer()

    result = analyzer.analyze(query="sql: select count(*) from accounts", min_query_chars=2)

    assert result.intent == "structured_query"
    assert result.need_retrieval is True
