"""FastAPI application entrypoint for Recruit Lens with security headers, /ready, and /metrics."""

import os
import resource
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app import __version__
from app.api.v1 import api_v1_router
from app.config import settings
from app.db.session import AsyncSessionLocal, init_db
from app.logging import request_id_ctx, setup_logging
from app.middleware import RequestIdMiddleware

_START_TIME = time.time()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security hardening response headers."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response


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

    # Security Headers Middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS Middleware locked to configured origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation Error",
                "detail": exc.errors(),
                "details": exc.errors(),
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "request_id": request_id_ctx.get(),
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exc.detail,
                    "status_code": exc.status_code,
                    "request_id": request_id_ctx.get(),
                },
            },
        )

    # Health & Readiness Probes
    @app.get("/health", tags=["Health"])
    @app.get("/healthz", tags=["Health"])
    async def health_check() -> dict[str, str]:
        """Liveness probe returning application health status."""
        return {
            "status": "ok",
            "version": __version__,
            "environment": settings.ENVIRONMENT,
            "request_id": request_id_ctx.get() or "unknown",
        }

    @app.get("/api/v1/ping", tags=["Health"])
    async def ping_check() -> dict[str, bool]:
        """Ping probe for API reachability."""
        return {"pong": True}

    @app.get("/ready", tags=["Health"])
    async def readiness_check() -> dict[str, Any]:
        """Readiness probe checking database connectivity and storage readiness."""
        db_healthy = False
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT 1"))
                db_healthy = True
        except Exception:
            db_healthy = False

        if not db_healthy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connectivity unavailable",
            )

        return {
            "status": "ready",
            "database": "connected",
            "storage": settings.STORAGE_BACKEND,
            "version": __version__,
        }

    @app.get("/metrics", tags=["Health"])
    async def metrics_endpoint() -> dict[str, Any]:
        """Operational metrics: memory RSS, process uptime, and configuration."""
        # Get memory usage in MB
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # On Linux, ru_maxrss is in KB
        rss_mb = usage.ru_maxrss / 1024.0

        uptime_seconds = time.time() - _START_TIME

        return {
            "process_rss_mb": round(rss_mb, 2),
            "process_uptime_seconds": round(uptime_seconds, 2),
            "active_storage_backend": settings.STORAGE_BACKEND,
            "embedding_model": settings.EMBEDDING_MODEL,
            "llm_cache_enabled": settings.LLM_CACHE_ENABLED,
            "pid": os.getpid(),
        }

    @app.post("/api/v1/echo", tags=["Testing"])
    async def echo_endpoint(payload: EchoPayload) -> dict[str, Any]:
        """Test endpoint to verify request ID propagation and typed input validation."""
        return {"echo": payload.message}

    # Mount frontend static build directory if present
    possible_dist_paths = [
        Path("/app/frontend/dist"),
        settings.PROJECT_ROOT / "frontend" / "dist",
        Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
    ]
    for dist_dir in possible_dist_paths:
        if dist_dir.is_dir() and (dist_dir / "index.html").exists():
            app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")
            break

    return app


app = create_app()
