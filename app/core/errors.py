import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.logging import correlation_id_var
from app.domain.exceptions import DomainError, ProfileAlreadyExistsError, ProfileNotFoundError

logger = logging.getLogger(__name__)

DOMAIN_STATUS_CODES: dict[type[DomainError], int] = {
    ProfileNotFoundError: 404,
    ProfileAlreadyExistsError: 409,
}
DEFAULT_DOMAIN_STATUS = 400
_LOCATION_ROOTS = {"body", "query", "path", "header", "cookie"}


class ErrorBody(BaseModel):
    code: str
    message: str
    correlationId: str | None
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            correlationId=correlation_id_var.get(),
            details=details,
        )
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(exclude_none=True))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        status_code = DOMAIN_STATUS_CODES.get(type(exc), DEFAULT_DOMAIN_STATUS)
        return _error_response(status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Solo se devuelven ubicación y mensaje, nunca el valor enviado (puede ser sensible).
        details = [
            {
                "field": ".".join(str(part) for part in error["loc"][1:])
                if error["loc"] and error["loc"][0] in _LOCATION_ROOTS
                else ".".join(str(part) for part in error["loc"]),
                "message": error["msg"],
            }
            for error in exc.errors()
        ]
        return _error_response(422, "VALIDATION_ERROR", "Datos de entrada no válidos", details)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", exc_info=exc)
        return _error_response(500, "INTERNAL_ERROR", "Error interno del servidor")
