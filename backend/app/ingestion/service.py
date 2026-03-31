from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import SUPPORTED_TEXT_EXTENSIONS, SUPPORTED_TEXT_MIME_TYPES
from app.db.models import Document, DocumentVersion
from app.domain.enums import DocumentStatus


class UnsupportedDocumentError(ValueError):
    pass


class SimpleDocumentIngestionService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._logger = logging.getLogger("app.ingestion")

    @staticmethod
    def _is_supported(filename: str, mime_type: str | None) -> bool:
        suffix = Path(filename).suffix.lower()
        if suffix in SUPPORTED_TEXT_EXTENSIONS:
            return True
        if mime_type and mime_type.lower() in SUPPORTED_TEXT_MIME_TYPES:
            return True
        return False

    @staticmethod
    def _decode_text(content_bytes: bytes) -> str:
        try:
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UnsupportedDocumentError("Only UTF-8 text files are supported") from exc

    def create_document(
        self,
        *,
        title: str,
        filename: str,
        mime_type: str | None,
        content_bytes: bytes,
        metadata: dict[str, Any],
        request_id: str,
        trace_id: str,
    ) -> Document:
        if not self._is_supported(filename, mime_type):
            raise UnsupportedDocumentError("Only txt/markdown uploads are supported")

        content_text = self._decode_text(content_bytes)
        content_sha256 = hashlib.sha256(content_bytes).hexdigest()

        document = Document(
            title=title,
            source_uri=f"upload://{filename}",
            mime_type=mime_type,
            status=DocumentStatus.RECEIVED,
            meta={"filename": filename, **metadata},
        )
        self._db.add(document)
        self._db.flush()

        version = DocumentVersion(
            document_id=document.id,
            version_number=1,
            content_sha256=content_sha256,
            content_text=content_text,
            content_uri=None,
            size_bytes=len(content_bytes),
            meta={"filename": filename},
        )
        self._db.add(version)
        self._db.commit()
        self._db.refresh(document)

        self._logger.info(
            "document_ingested",
            extra={
                "request_id": request_id,
                "trace_id": trace_id,
                "document_id": str(document.id),
                "provider_name": "upload",
                "fallback_used": False,
                "size_bytes": len(content_bytes),
            },
        )
        return document

    def list_documents(self, *, limit: int = 50, offset: int = 0) -> tuple[list[Document], int]:
        rows = self._db.execute(
            select(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset)
        ).scalars().all()
        total = self._db.query(Document).count()
        return rows, total
