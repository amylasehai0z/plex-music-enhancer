"""FastAPI exception handlers."""

from __future__ import annotations

from plex_music_enhancer.api.errors import APIError


def register_exception_handlers(app) -> None:
    """Register centralized exception handlers."""
    from fastapi import Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        """Map internal API errors to JSON responses."""
        return JSONResponse(status_code=exc.status_code, content=exc.to_problem())

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Map request validation failures to HTTP 400."""
        return JSONResponse(
            status_code=400,
            content={
                "code": "validation_error",
                "message": "Request validation failed.",
                "statusCode": 400,
                "details": {"errors": exc.errors()},
            },
        )
