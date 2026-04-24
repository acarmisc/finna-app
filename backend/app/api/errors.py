"""Error handling and response models for FastAPI."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# Error response schemas for OpenAPI documentation
class ErrorDetail(BaseModel):
    """Error response detail model."""
    error: str = Field(..., description="Error type code")
    message: str = Field(..., description="Human-readable error message")
    detail: dict[str, Any] | None = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    message: str
    detail: dict[str, Any] | None = None
    path: str | None = None
    method: str | None = None


# Standard error definitions
class APIError(Exception):
    """Base exception for API errors."""
    def __init__(
        self,
        status_code: int,
        error: str,
        message: str,
        detail: dict[str, Any] | None = None,
    ):
        self.status_code = status_code
        self.error = error
        self.message = message
        self.detail = detail or {}
        super().__init__(message)


class NotFoundError(APIError):
    """404 Not Found error."""
    def __init__(self, resource: str, identifier: str | None = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} '{identifier}' not found"
        super().__init__(404, "not_found", message)


class ForbiddenError(APIError):
    """403 Forbidden error."""
    def __init__(self, message: str = "Forbidden"):
        super().__init__(403, "forbidden", message)


class UnauthorizedError(APIError):
    """401 Unauthorized error."""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(401, "unauthorized", message)


class ValidationError(APIError):
    """422 Validation error."""
    def __init__(self, message: str = "Validation failed", details: dict[str, Any] | None = None):
        super().__init__(422, "validation_error", message, details)


class RateLimitError(APIError):
    """429 Rate limit exceeded error."""
    def __init__(self, retry_after: int):
        super().__init__(
            429,
            "rate_limit_exceeded",
            "Too many requests. Please retry after some time.",
            {"retry_after": retry_after},
        )


async def error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Convert APIError exceptions to JSON responses."""
    response = ErrorResponse(
        error=exc.error,
        message=exc.message,
        detail=exc.detail,
        path=str(request.url.path),
        method=request.method,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(),
    )


async def validation_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle Pydantic/Starlette validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Validation failed",
            "detail": {"errors": str(exc)},
            "path": str(request.url.path),
            "method": request.method,
        },
    )


async def http_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle HTTPException errors."""
    # Starlette HTTPException has status_code and detail attributes
    status_code = getattr(exc, "status_code", 500)
    detail = getattr(exc, "detail", str(exc))
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": "http_error",
            "message": str(detail),
            "path": str(request.url.path),
            "method": request.method,
        },
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle all other exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred",
            "path": str(request.url.path),
            "method": request.method,
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register custom error handlers with FastAPI app."""
    app.add_exception_handler(APIError, error_handler)
    app.add_exception_handler(422, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
