from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import (
    handle_app_error,
    handle_http_exception,
    handle_unexpected_exception,
    handle_validation_error,
)
from app.api.routes import router
from app.core.config import get_settings
from app.core.errors import AppError
from app.observability.logging import configure_logging
from app.observability.middleware import RequestContextMiddleware


settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Production-grade Agentic RAG backend",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=settings.cors_allowed_methods,
    allow_headers=settings.cors_allowed_headers,
)
app.add_middleware(RequestContextMiddleware)
app.include_router(router)

app.add_exception_handler(AppError, handle_app_error)
app.add_exception_handler(RequestValidationError, handle_validation_error)
app.add_exception_handler(HTTPException, handle_http_exception)
app.add_exception_handler(Exception, handle_unexpected_exception)
