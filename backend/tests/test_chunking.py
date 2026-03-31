from uuid import uuid4

from app.indexing.chunker import SlidingWindowChunker


def test_sliding_window_chunker_generates_stable_spans() -> None:
    text = "abcdefghij" * 30
    chunker = SlidingWindowChunker(chunk_size=50, chunk_overlap=10)
    chunks = chunker.chunk(
        text=text,
        document_id=uuid4(),
        document_version_id=uuid4(),
        metadata={"lang": "en"},
    )

    assert len(chunks) >= 2
    assert chunks[0].start_char == 0
    assert chunks[0].end_char == 50
    assert chunks[1].start_char == 40
    assert chunks[1].metadata["lang"] == "en"
