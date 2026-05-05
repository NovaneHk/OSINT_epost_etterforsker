"""
Unit tests for core/error_handling.py
Covers custom exception classes and StructuredLogger basics.
"""

import pytest
from core.error_handling import (
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    CustomError,
    ValidationError,
    NetworkError,
    DatabaseError,
    RateLimitError,
    StructuredLogger,
)


# ---------------------------------------------------------------------------
# Custom exception classes
# ---------------------------------------------------------------------------

class TestCustomError:
    def test_basic_creation(self):
        err = CustomError("something went wrong")
        assert str(err) == "something went wrong"
        assert err.message == "something went wrong"
        assert err.severity == ErrorSeverity.MEDIUM
        assert err.category == ErrorCategory.BUSINESS_LOGIC

    def test_custom_severity(self):
        err = CustomError("oops", severity=ErrorSeverity.CRITICAL)
        assert err.severity == ErrorSeverity.CRITICAL

    def test_default_context_created(self):
        err = CustomError("msg")
        assert err.context.operation == "unknown"

    def test_resolution_suggestions_default_empty(self):
        err = CustomError("msg")
        assert err.resolution_suggestions == []


class TestValidationError:
    def test_creation_with_field_and_value(self):
        err = ValidationError("bad email", field="email", value="not-an-email")
        assert err.field == "email"
        assert err.value == "not-an-email"
        assert "bad email" in str(err)

    def test_creation_without_optional_args(self):
        err = ValidationError("required")
        assert err.field is None
        assert err.value is None


class TestNetworkError:
    def test_creation_with_url_and_status(self):
        err = NetworkError("timeout", url="https://example.com", status_code=504)
        assert err.url == "https://example.com"
        assert err.status_code == 504

    def test_creation_without_optional_args(self):
        err = NetworkError("connection refused")
        assert err.url is None
        assert err.status_code is None


class TestDatabaseError:
    def test_creation_with_query(self):
        err = DatabaseError("query failed", query="SELECT * FROM users")
        assert err.query == "SELECT * FROM users"

    def test_creation_without_query(self):
        err = DatabaseError("connection error")
        assert err.query is None


class TestRateLimitError:
    def test_creation_with_retry_after(self):
        err = RateLimitError("too many requests", retry_after=60)
        assert err.retry_after == 60

    def test_creation_without_retry_after(self):
        err = RateLimitError("slow down")
        assert err.retry_after is None


# ---------------------------------------------------------------------------
# ErrorContext dataclass
# ---------------------------------------------------------------------------

class TestErrorContext:
    def test_required_fields(self):
        ctx = ErrorContext(operation="scrape", component="crawler")
        assert ctx.operation == "scrape"
        assert ctx.component == "crawler"

    def test_optional_fields_default_none(self):
        ctx = ErrorContext("op", "comp")
        assert ctx.user_id is None
        assert ctx.session_id is None
        assert ctx.request_id is None


# ---------------------------------------------------------------------------
# StructuredLogger
# ---------------------------------------------------------------------------

class TestStructuredLogger:
    def test_initialization(self):
        logger = StructuredLogger("test_logger")
        assert logger.logger is not None
        assert logger.error_reports == []

    def test_log_error_standard_exception(self):
        logger = StructuredLogger("test_logger2")
        report = logger.log_error(ValueError("test error"))
        assert report is not None
        assert report.exception_type == "ValueError"

    def test_log_error_custom_exception(self):
        logger = StructuredLogger("test_logger3")
        err = CustomError("custom", severity=ErrorSeverity.HIGH)
        report = logger.log_error(err)
        assert report.severity == ErrorSeverity.HIGH

    def test_log_error_appends_to_reports(self):
        logger = StructuredLogger("test_logger4")
        logger.log_error(RuntimeError("err1"))
        logger.log_error(RuntimeError("err2"))
        assert len(logger.error_reports) == 2

    def test_get_error_statistics_empty(self):
        logger = StructuredLogger("test_logger5")
        stats = logger.get_error_statistics()
        assert stats["total_errors"] == 0

    def test_get_error_statistics_with_errors(self):
        logger = StructuredLogger("test_logger6")
        logger.log_error(ValueError("e1"))
        logger.log_error(TypeError("e2"))
        stats = logger.get_error_statistics()
        assert stats["total_errors"] >= 2
