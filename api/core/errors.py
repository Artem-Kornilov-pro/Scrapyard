import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from api.core.config import settings

logger = logging.getLogger(__name__)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for exceptions that aren't already an HTTPException.

    FastAPI's own handlers for HTTPException/RequestValidationError take
    priority over this (Starlette dispatches to the most specific
    registered handler), so this only fires for genuine bugs — a
    KeyError, a driver-level exception, etc. The full traceback always
    goes to the logs; the response body only includes the exception
    text when DEBUG is on, so production responses don't leak internals.
    """
    logger.exception(
        "Unhandled exception on %s %s", request.method, request.url.path
    )
    detail = str(exc) if settings.debug else "Internal server error"
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": detail},
    )
