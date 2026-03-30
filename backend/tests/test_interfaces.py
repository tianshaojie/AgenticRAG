from app.domain import interfaces


def test_required_interface_symbols_exist() -> None:
    required = [
        'DocumentIngestor',
        'Chunker',
        'Embedder',
        'VectorIndex',
        'Retriever',
        'Reranker',
        'CitationAssembler',
        'AnswerGenerator',
        'AgentPolicy',
        'EvaluationRunner',
    ]
    for name in required:
        assert hasattr(interfaces, name)
