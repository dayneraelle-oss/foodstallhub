"""Custom exceptions and FastAPI exception handlers."""

from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.utils.logger import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Expected, user-facing error with an HTTP status code."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        code: Optional[str] = None,
        headers: Optional[dict] = None,
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.code = code or "app_error"
        self.headers = headers


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError):
        body = {"detail": exc.detail, "code": exc.code}
        return JSONResponse(
            status_code=exc.status_code,
            content=body,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError):
        logger.warning("Validation error: %s", exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Request validation failed",
                "code": "validation_error",
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception):
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "code": "internal_error"},
        )