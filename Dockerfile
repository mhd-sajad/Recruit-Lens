# syntax=docker/dockerfile:1.4
# Multi-stage production Dockerfile for Recruit Lens

# ==============================================================================
# Stage 1: Build Frontend Assets
# ==============================================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Build Backend Environment & Dependencies
# ==============================================================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS backend-builder
WORKDIR /app/backend

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY backend/ ./
RUN uv sync --frozen --no-dev

# ==============================================================================
# Stage 3: Production Runtime
# ==============================================================================
FROM python:3.11-slim-bookworm AS runtime

# Install curl for container health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system user
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -d /app -s /bin/bash appuser

WORKDIR /app

# Copy virtual environment and application code
ENV VIRTUAL_ENV=/app/backend/.venv
ENV PATH="/app/backend/.venv/bin:$PATH"
ENV PYTHONPATH="/app/backend"
ENV ENVIRONMENT=production

COPY --from=backend-builder /app/backend/.venv /app/backend/.venv
COPY --from=backend-builder /app/backend /app/backend
COPY --from=frontend-builder /frontend/dist /app/frontend/dist
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

# Set ownership and permissions
RUN chown -R appuser:appuser /app && \
    chmod +x /app/docker-entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
