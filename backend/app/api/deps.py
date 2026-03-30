from fastapi import Request

from app.schemas.common import RequestMetadata


def get_request_metadata(request: Request) -> RequestMetadata:
    request_id = getattr(request.state, "request_id", "unknown")
    trace_id = getattr(request.state, "trace_id", "unknown")
    return RequestMetadata(request_id=request_id, trace_id=trace_id)
