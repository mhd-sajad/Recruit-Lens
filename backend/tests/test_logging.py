"""Tests for structured logging and PII scrubbing."""

import logging

from app.logging import StructuredJsonFormatter, sanitize_pii, setup_logging


def test_sanitize_pii() -> None:
    """Verify email and phone redaction in logs."""
    raw = "User candidate John with email john.doe@example.com and phone +1-555-123-4567 applied."
    sanitized = sanitize_pii(raw)
    assert "john.doe@example.com" not in sanitized
    assert "[REDACTED_EMAIL]" in sanitized
    assert "[REDACTED_PHONE]" in sanitized


def test_structured_json_formatter() -> None:
    """Verify JSON formatter outputs expected fields."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message with email user@corp.org",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert '"level": "INFO"' in formatted
    assert '"logger": "test_logger"' in formatted
    assert "[REDACTED_EMAIL]" in formatted
    assert "user@corp.org" not in formatted


def test_setup_logging_text_and_json() -> None:
    """Verify setup_logging configures root handlers for text and json."""
    setup_logging(log_level="DEBUG", log_format="json")
    root = logging.getLogger()
    assert len(root.handlers) > 0

    setup_logging(log_level="INFO", log_format="text")
    assert len(root.handlers) > 0
