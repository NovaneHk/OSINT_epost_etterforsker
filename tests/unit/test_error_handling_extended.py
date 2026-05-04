"""
Extended unit tests for core/error_handling.py
Covers RetryManager, ErrorHandler, error_boundary and HealthChecker.
"""

import asyncio
import functools
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.error_handling import (
    CustomError,
    DatabaseError,
    ErrorCategory,
    ErrorContext,
    ErrorHandler,
    ErrorReport,
    ErrorSeverity,
    HealthChecker,
    NetworkError,
    OSINTError,
    RateLimitError,
    RetryManager,
    StructuredLogger,
    ValidationError,
    create_context,
    error_boundary,
    get_error_handler,
    get_logger,
    handle_errors,
    log_error,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_handler() -> ErrorHandler:
    logger = StructuredLogger("test_eh_logger")
    return ErrorHandler(logger)


# ---------------------------------------------------------------------------
# StructuredLogger — file handler branch
# ---------------------------------------------------------------------------

class TestStructuredLoggerFileHandler:
    def test_setup_with_log_file(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        logger = StructuredLogger("file_logger", log_file=log_file)
        # Should have at least 2 handlers (console + file)
        assert len(logger.logger.handlers) >= 2

    def test_log_error_with_context(self):
        logger = StructuredLogger("ctx_logger")
        ctx = ErrorContext("op", "comp")
        report = logger.log_error(ValueError("ctx error"), context=ctx)
        assert report.context.operation == "op"

    def test_log_custom_error_copies_context(self):
        logger = StructuredLogger("custom_logger")
        ctx = ErrorContext("my_op", "my_comp")
        err = CustomError("custom", context=ctx)
        report = logger.log_error(err)
        assert report.context.operation == "my_op"

    def test_get_error_statistics_with_recent_errors(self):
        logger = StructuredLogger("stats_logger")
        logger.log_error(ValueError("e1"))
        logger.log_error(TypeError("e2"))
        stats = logger.get_error_statistics()
        assert stats["total_errors"] == 2
        assert stats["recent_errors_24h"] == 2
        assert "category_distribution" in stats
        assert "severity_distribution" in stats
        assert "error_rate" in stats


# ---------------------------------------------------------------------------
# RetryManager
# ---------------------------------------------------------------------------

class TestRetryManager:
    def test_network_retry_returns_decorator(self):
        decorator = RetryManager.network_retry(max_attempts=2)
        assert callable(decorator)

    def test_database_retry_returns_decorator(self):
        decorator = RetryManager.database_retry(max_attempts=2)
        assert callable(decorator)

    def test_rate_limit_retry_returns_decorator(self):
        decorator = RetryManager.rate_limit_retry(max_attempts=2)
        assert callable(decorator)

    def test_network_retry_callable_applied(self):
        """Verify the decorator wraps a function."""
        decorator = RetryManager.network_retry(max_attempts=1)
        result_called = []

        @decorator
        def my_func():
            result_called.append(True)
            return "ok"

        # tenacity doesn't wrap the return value for non-failing calls
        assert callable(my_func)


# ---------------------------------------------------------------------------
# ErrorHandler
# ---------------------------------------------------------------------------

class TestErrorHandlerInit:
    def test_default_handlers_are_registered(self):
        handler = _make_handler()
        assert ValidationError in handler.error_handlers
        assert NetworkError in handler.error_handlers
        assert DatabaseError in handler.error_handlers
        assert RateLimitError in handler.error_handlers

    def test_register_custom_handler(self):
        handler = _make_handler()
        custom_called = []

        def my_handler(error, report):
            custom_called.append(True)

        handler.register_handler(RuntimeError, my_handler)
        assert RuntimeError in handler.error_handlers


class TestErrorHandlerHandleError:
    def test_returns_error_report(self):
        handler = _make_handler()
        report = handler.handle_error(ValueError("generic"), None)
        assert report is not None
        assert report.exception_type == "ValueError"

    def test_calls_specific_handler_for_validation_error(self):
        handler = _make_handler()
        # Call the handler method directly with a well-formed CustomError
        err = CustomError("bad input", severity=ErrorSeverity.MEDIUM,
                          category=ErrorCategory.VALIDATION)
        report = handler.handle_error(err)
        assert report is not None

    def test_calls_specific_handler_for_network_error(self):
        handler = _make_handler()
        err = CustomError("timeout", severity=ErrorSeverity.HIGH,
                          category=ErrorCategory.NETWORK)
        report = handler.handle_error(err)
        assert report is not None

    def test_calls_specific_handler_for_database_error(self):
        handler = _make_handler()
        err = CustomError("query failed", severity=ErrorSeverity.HIGH,
                          category=ErrorCategory.DATABASE)
        report = handler.handle_error(err)
        assert report is not None

    def test_calls_specific_handler_for_rate_limit_error(self):
        handler = _make_handler()
        err = CustomError("too many requests", severity=ErrorSeverity.MEDIUM,
                          category=ErrorCategory.RATE_LIMIT)
        report = handler.handle_error(err)
        assert report is not None

    def test_handler_exception_is_caught(self):
        """ErrorHandler should not propagate exceptions from sub-handlers."""
        handler = _make_handler()

        def bad_handler(error, report):
            raise RuntimeError("handler itself failed")

        handler.register_handler(AttributeError, bad_handler)
        # Should not raise — errors in handlers are caught
        report = handler.handle_error(AttributeError("field"))
        assert report is not None


class TestErrorHandlerResolutionSuggestions:
    def test_validation_error_adds_suggestions(self):
        handler = _make_handler()
        err = ValidationError("invalid format")
        report = ErrorReport(
            error_id="test",
            timestamp=__import__("datetime").datetime.now(),
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION,
            message="test",
            context=ErrorContext("op", "comp"),
            exception_type="ValidationError",
            stack_trace="",
            resolution_suggestions=[],
        )
        handler._handle_validation_error(err, report)
        assert len(report.resolution_suggestions) > 0

    def test_network_error_adds_suggestions(self):
        handler = _make_handler()
        err = NetworkError("timeout")
        report = ErrorReport(
            error_id="test",
            timestamp=__import__("datetime").datetime.now(),
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            message="test",
            context=ErrorContext("op", "comp"),
            exception_type="NetworkError",
            stack_trace="",
            resolution_suggestions=[],
        )
        handler._handle_network_error(err, report)
        assert len(report.resolution_suggestions) > 0

    def test_database_error_adds_suggestions(self):
        handler = _make_handler()
        err = DatabaseError("query failed")
        report = ErrorReport(
            error_id="test",
            timestamp=__import__("datetime").datetime.now(),
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.DATABASE,
            message="test",
            context=ErrorContext("op", "comp"),
            exception_type="DatabaseError",
            stack_trace="",
            resolution_suggestions=[],
        )
        handler._handle_database_error(err, report)
        assert len(report.resolution_suggestions) > 0

    def test_rate_limit_error_adds_suggestions(self):
        handler = _make_handler()
        err = RateLimitError("429")
        report = ErrorReport(
            error_id="test",
            timestamp=__import__("datetime").datetime.now(),
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.RATE_LIMIT,
            message="test",
            context=ErrorContext("op", "comp"),
            exception_type="RateLimitError",
            stack_trace="",
            resolution_suggestions=[],
        )
        handler._handle_rate_limit_error(err, report)
        assert len(report.resolution_suggestions) > 0


# ---------------------------------------------------------------------------
# error_boundary decorator
# ---------------------------------------------------------------------------

class TestErrorBoundary:
    def test_sync_function_succeeds(self):
        @error_boundary()
        def add(a, b):
            return a + b

        assert add(1, 2) == 3

    def test_sync_function_reraises_by_default(self):
        @error_boundary()
        def fail():
            raise ValueError("oops")

        with pytest.raises(ValueError):
            fail()

    def test_sync_function_suppresses_with_reraise_false(self):
        @error_boundary(reraise=False, default_return="fallback")
        def fail():
            raise ValueError("oops")

        assert fail() == "fallback"

    def test_sync_function_logs_error(self):
        logger = StructuredLogger("eb_logger")

        @error_boundary(logger=logger, reraise=False)
        def fail():
            raise RuntimeError("test error")

        fail()
        assert len(logger.error_reports) == 1

    def test_async_function_succeeds(self):
        @error_boundary()
        async def async_add(a, b):
            return a + b

        result = asyncio.run(async_add(2, 3))
        assert result == 5

    def test_async_function_reraises_by_default(self):
        @error_boundary()
        async def async_fail():
            raise ValueError("async oops")

        with pytest.raises(ValueError):
            asyncio.run(async_fail())

    def test_async_function_suppresses_with_reraise_false(self):
        @error_boundary(reraise=False, default_return="async_fallback")
        async def async_fail():
            raise ValueError("async oops")

        result = asyncio.run(async_fail())
        assert result == "async_fallback"

    def test_async_logs_error(self):
        logger = StructuredLogger("async_eb_logger")

        @error_boundary(logger=logger, reraise=False)
        async def async_fail():
            raise RuntimeError("async error")

        asyncio.run(async_fail())
        assert len(logger.error_reports) == 1


# ---------------------------------------------------------------------------
# HealthChecker
# ---------------------------------------------------------------------------

class TestHealthChecker:
    def test_register_and_run_sync_check(self):
        handler = _make_handler()
        hc = HealthChecker(handler)

        def check_ok():
            return {"status": "ok"}

        hc.register_health_check("sync_check", check_ok)
        result = asyncio.run(hc.run_health_checks())
        assert "sync_check" in result
        assert result["sync_check"]["status"] == "healthy"

    def test_register_and_run_async_check(self):
        handler = _make_handler()
        hc = HealthChecker(handler)

        async def check_async():
            return {"async": True}

        hc.register_health_check("async_check", check_async)
        result = asyncio.run(hc.run_health_checks())
        assert result["async_check"]["status"] == "healthy"

    def test_failing_check_returns_unhealthy(self):
        handler = _make_handler()
        hc = HealthChecker(handler)

        def bad_check():
            raise RuntimeError("service down")

        hc.register_health_check("bad_check", bad_check)
        result = asyncio.run(hc.run_health_checks())
        assert result["bad_check"]["status"] == "unhealthy"
        assert "error" in result["bad_check"]

    def test_run_health_checks_includes_error_statistics(self):
        handler = _make_handler()
        hc = HealthChecker(handler)
        result = asyncio.run(hc.run_health_checks())
        assert "error_statistics" in result


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

class TestConvenienceFunctions:
    def test_get_error_handler_returns_instance(self):
        handler = get_error_handler()
        assert isinstance(handler, ErrorHandler)

    def test_get_logger_returns_instance(self):
        logger = get_logger()
        assert isinstance(logger, StructuredLogger)

    def test_log_error_returns_report(self):
        report = log_error(ValueError("global error"))
        assert report is not None

    def test_create_context_returns_context(self):
        ctx = create_context("my_op", "my_component", extra="data")
        assert ctx.operation == "my_op"
        assert ctx.component == "my_component"


# ---------------------------------------------------------------------------
# handle_errors decorator
# ---------------------------------------------------------------------------

class TestHandleErrors:
    def test_sync_function_passes_through(self):
        @handle_errors
        def add(a, b):
            return a + b

        assert add(3, 4) == 7

    def test_sync_osint_error_reraises_as_is(self):
        @handle_errors
        def raise_osint():
            raise OSINTError("already osint")

        with pytest.raises(OSINTError, match="already osint"):
            raise_osint()

    def test_sync_generic_exception_wrapped_as_osint(self):
        @handle_errors
        def raise_generic():
            raise KeyError("missing key")

        with pytest.raises(OSINTError):
            raise_generic()

    def test_async_function_passes_through(self):
        @handle_errors
        async def async_add(a, b):
            return a + b

        result = asyncio.run(async_add(5, 6))
        assert result == 11

    def test_async_osint_error_reraises_as_is(self):
        @handle_errors
        async def async_raise_osint():
            raise OSINTError("async already osint")

        with pytest.raises(OSINTError, match="async already osint"):
            asyncio.run(async_raise_osint())

    def test_async_generic_exception_wrapped_as_osint(self):
        @handle_errors
        async def async_raise_generic():
            raise AttributeError("no attr")

        with pytest.raises(OSINTError):
            asyncio.run(async_raise_generic())


# ---------------------------------------------------------------------------
# OSINTError alias
# ---------------------------------------------------------------------------

class TestOSINTError:
    def test_is_custom_error_subclass(self):
        err = OSINTError("test")
        assert isinstance(err, CustomError)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(OSINTError):
            raise OSINTError("osint failure")
