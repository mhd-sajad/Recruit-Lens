"""Tests for application configuration and settings validation."""

from pathlib import Path

import pytest
from app.config import Settings
from pydantic import ValidationError


def test_default_settings() -> None:
    """Verify default settings values and path resolutions."""
    cfg = Settings()
    assert cfg.ENVIRONMENT in ["development", "testing", "production"]
    assert cfg.APP_PORT == 8000
    assert cfg.MAX_BATCH_RESUMES == 200
    assert cfg.MAX_UPLOAD_FILE_SIZE_MB == 10
    assert isinstance(cfg.PROJECT_ROOT, Path)
    assert cfg.data_dir.exists()


def test_cors_origins_parsing() -> None:
    """Verify CORS origins string parsing."""
    cfg = Settings(CORS_ORIGINS='["http://example.com", "http://app.local"]')  # type: ignore[arg-type]
    assert "http://example.com" in cfg.CORS_ORIGINS
    assert "http://app.local" in cfg.CORS_ORIGINS

    cfg2 = Settings(CORS_ORIGINS="http://alpha.com, http://beta.com")  # type: ignore[arg-type]
    assert "http://alpha.com" in cfg2.CORS_ORIGINS
    assert "http://beta.com" in cfg2.CORS_ORIGINS


def test_invalid_port_validation() -> None:
    """Verify invalid port values are rejected by pydantic."""
    with pytest.raises(ValidationError):
        Settings(APP_PORT=999999)

    with pytest.raises(ValidationError):
        Settings(APP_PORT=0)


def test_invalid_limits() -> None:
    """Verify out-of-range batch limits are rejected."""
    with pytest.raises(ValidationError):
        Settings(MAX_BATCH_RESUMES=0)

    with pytest.raises(ValidationError):
        Settings(MAX_UPLOAD_FILE_SIZE_MB=0)
