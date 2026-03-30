from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.observability.logging import configure_logging
from app.observability.middleware import RequestContextMiddleware


settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Step 1 scaffold for production-grade Agentic RAG",
)
app.add_middleware(RequestContextMiddleware)
app.include_router(router)
