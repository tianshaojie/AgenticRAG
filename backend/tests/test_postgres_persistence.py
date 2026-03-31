import pytest
from sqlalchemy import desc, select

from app.db.models import DocumentVersion
from app.ingestion.service import SimpleDocumentIngestionService


@pytest.mark.integration
def test_document_and_version_persisted(db_session) -> None:
    service = SimpleDocumentIngestionService(db_session)
    doc = service.create_document(
        title="Doc1",
        filename="doc1.md",
        mime_type="text/markdown",
        content_bytes=b"# Title\\nhello",
        metadata={"source": "test"},
        request_id="req-test",
        trace_id="trace-test",
    )

    assert doc.id is not None
    assert doc.meta["source"] == "test"

    version = db_session.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc.id)
        .order_by(desc(DocumentVersion.version_number))
        .limit(1)
    ).scalar_one()

    assert version.content_text.startswith("# Title")
