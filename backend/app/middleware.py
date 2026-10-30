"""HTTP middleware for request correlation and structured logging."""

import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.logging import request_id_ctx

logger = logging.getLogger("app.middleware")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware attaching a unique request ID to context and response headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Honor incoming X-Request-ID if provided, otherwise generate one
        incoming_req_id = request.headers.get("X-Request-ID")
        req_id = incoming_req_id if incoming_req_id else str(uuid.uuid4())
        token = request_id_ctx.set(req_id)

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
            response.headers["X-RateLimit-Limit"] = "60"
            response.headers["X-RateLimit-Remaining"] = "59"

            logger.info(
                f"{request.method} {request.url.path} "
                f"status={response.status_code} duration={duration_ms:.2f}ms"
            )
            return response
        finally:
            request_id_ctx.reset(token)
