from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.common import RequestMetadata


def get_request_metadata(request: Request) -> RequestMetadata:
    request_id = getattr(request.state, "request_id", "unknown")
    trace_id = getattr(request.state, "trace_id", "unknown")
    return RequestMetadata(request_id=request_id, trace_id=trace_id)


def get_db(request_session: Session = Depends(get_db_session)) -> Session:
    return request_session
