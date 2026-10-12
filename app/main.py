import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from app.api.routes import health
from app.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.ids import new_uuid7
from app.core.logging import configure_logging, correlation_id_var

CORRELATION_HEADER = "X-Correlation-Id"

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "service_started", extra={"extra_fields": {"environment": get_settings().environment}}
    )
    yield
    logger.info("service_stopped")


def _resolve_correlation_id(header_value: str | None) -> str:
    if header_value:
        try:
            return str(uuid.UUID(header_value))
        except ValueError:
            pass
    return str(new_uuid7())


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    is_prod = settings.environment == "prod"
    app = FastAPI(
        title="profile-service",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if is_prod else "/openapi.json",
    )

    @app.middleware("http")
    async def correlation_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlation_id = _resolve_correlation_id(request.headers.get(CORRELATION_HEADER))
        token = correlation_id_var.set(correlation_id)
        try:
            response = await call_next(request)
            logger.info(
                "request_completed",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "status": response.status_code,
                    }
                },
            )
        finally:
            correlation_id_var.reset(token)
        response.headers[CORRELATION_HEADER] = correlation_id
        return response

    register_exception_handlers(app)
    app.include_router(health.router)
    return app


app = create_app()
