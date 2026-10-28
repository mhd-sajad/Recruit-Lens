"""FastAPI application entrypoint for Recruit Lens."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import __version__
from app.api.v1 import api_v1_router
from app.config import settings
from app.db.session import init_db
from app.logging import request_id_ctx, setup_logging
from app.middleware import RequestIdMiddleware


class EchoPayload(BaseModel):
    """Echo payload for input validation testing."""

    message: str = Field(..., min_length=1, max_length=500)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management."""
    setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
    await init_db()
    yield


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    app = FastAPI(
        title="Recruit Lens API",
        version=__version__,
        description="Explainable, evidence-grounded AI recruiter platform API",
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID Middleware
    app.add_middleware(RequestIdMiddleware)

    # Mount API v1 Routers
    app.include_router(api_v1_router)

    # 4xx Error Handling (Never return 5xx on invalid client inputs)
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "error": "Validation Error",
                "detail": exc.errors(),
                "request_id": request_id_ctx.get(),
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "request_id": request_id_ctx.get(),
            },
        )

    @app.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
    async def health_check() -> dict[str, Any]:
        """Health check endpoint for container and uptime monitoring."""
        return {
            "status": "ok",
            "version": __version__,
            "environment": settings.ENVIRONMENT,
        }

    @app.get("/api/v1/ping", status_code=status.HTTP_200_OK, tags=["System"])
    async def ping() -> dict[str, bool]:
        """Simple ping endpoint for network latency validation."""
        return {"pong": True}

    @app.post("/api/v1/echo", status_code=status.HTTP_200_OK, tags=["System"])
    async def echo(payload: EchoPayload) -> dict[str, str]:
        """Validated echo endpoint for testing input validation and 4xx rules."""
        return {"echo": payload.message}

    return app


app = create_app()
