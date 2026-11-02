"""
Standardized API Exceptions and Error Response Handlers
"""
from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException


class APIError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class CancerNotFoundError(APIError):
    def __init__(self, identifier: str):
        super().__init__(
            code="CANCER_NOT_FOUND",
            message=f"Cancer '{identifier}' could not be found.",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"identifier": identifier},
        )


class CategoryNotFoundError(APIError):
    def __init__(self, category: str):
        super().__init__(
            code="CATEGORY_NOT_FOUND",
            message=f"Category '{category}' is not a recognized canonical category.",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"category": category},
        )


class AmbiguousCancerError(APIError):
    def __init__(self, identifier: str):
        super().__init__(
            code="AMBIGUOUS_CANCER",
            message="Cancer identifier is ambiguous. Use a canonical ID or slug.",
            status_code=status.HTTP_409_CONFLICT,
            details={"identifier": identifier},
        )


class SourceNotFoundError(APIError):
    def __init__(self, source_id: str):
        super().__init__(
            code="SOURCE_NOT_FOUND",
            message=f"Source '{source_id}' could not be found in the Source Registry.",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"source_id": source_id},
        )


class RateLimitExceededError(APIError):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message="Rate limit exceeded. Please wait before making more requests.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after_seconds": retry_after},
        )


class UnauthorizedError(APIError):
    def __init__(self, message: str = "Invalid or missing administrative credentials."):
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while processing the request.",
                "details": {},
            }
        },
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Do not echo request input, bodies, or exception contexts into diagnostics.
    issues = [{"location": list(e["loc"]), "type": e["type"], "message": e["msg"]}
              for e in exc.errors()]
    return JSONResponse(status_code=422, content={"error": {
        "code": "VALIDATION_ERROR", "message": "Request validation failed.",
        "details": {"issues": issues},
    }})


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    messages = {404: ("NOT_FOUND", "Requested path was not found."),
                405: ("METHOD_NOT_ALLOWED", "Method is not allowed for this path.")}
    code, message = messages.get(exc.status_code, ("HTTP_ERROR", "Request could not be completed."))
    return JSONResponse(status_code=exc.status_code, headers=exc.headers,
                        content={"error": {"code": code, "message": message, "details": {}}})
