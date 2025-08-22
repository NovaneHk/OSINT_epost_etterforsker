"""
Comprehensive Error Handling and Logging System
Advanced error handling, retry mechanisms, and structured logging
"""

import logging
import sys
import traceback
import asyncio
import functools
import time
from typing import Any, Callable, Dict, List, Optional, Type, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json

# Third-party imports
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)
import aiohttp
import requests


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    NETWORK = "network"
    VALIDATION = "validation"
    DATABASE = "database"
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    PARSING = "parsing"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"


@dataclass
class ErrorContext:
    """Context information for errors"""
    operation: str
    component: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class ErrorReport:
    """Structured error report"""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    context: ErrorContext
    exception_type: str
    stack_trace: str
    resolution_suggestions: List[str]
    retry_count: int = 0
    resolved: bool = False


class CustomError(Exception):
    """Base custom exception with structured information"""

    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 category: ErrorCategory = ErrorCategory.BUSINESS_LOGIC,
                 context: Optional[ErrorContext] = None,
                 resolution_suggestions: Optional[List[str]] = None):
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.category = category
        self.context = context or ErrorContext("unknown", "unknown")
        self.resolution_suggestions = resolution_suggestions or []
        self.timestamp = datetime.now()


class ValidationError(CustomError):
    """Validation-specific error"""
    def __init__(self, message: str, field: str = None, value: Any = None, **kwargs):
        super().__init__(message, ErrorCategory.VALIDATION, **kwargs)
        self.field = field
        self.value = value


class NetworkError(CustomError):
    """Network-related error"""
    def __init__(self, message: str, url: str = None, status_code: int = None, **kwargs):
        super().__init__(message, ErrorCategory.NETWORK, **kwargs)
        self.url = url
        self.status_code = status_code


class DatabaseError(CustomError):
    """Database-related error"""
    def __init__(self, message: str, query: str = None, **kwargs):
        super().__init__(message, ErrorCategory.DATABASE, **kwargs)
        self.query = query


class RateLimitError(CustomError):
    """Rate limiting error"""
    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, ErrorCategory.RATE_LIMIT, **kwargs)
        self.retry_after = retry_after


class StructuredLogger:
    """Enhanced logger with structured logging capabilities"""

    def __init__(self, name: str, log_file: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.setup_logging(log_file)
        self.error_reports: List[ErrorReport] = []

    def setup_logging(self, log_file: Optional[str] = None):
        """Setup structured logging configuration"""
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        self.logger.setLevel(logging.DEBUG)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s | '
            'file:%(filename)s:%(lineno)d | func:%(funcName)s'
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def log_error(self, error: Union[Exception, CustomError], context: Optional[ErrorContext] = None):
        """Log structured error with full context"""
        error_id = f"ERR_{int(time.time())}_{id(error)}"

        if isinstance(error, CustomError):
            severity = error.severity
            category = error.category
            context = error.context or context
            resolution_suggestions = error.resolution_suggestions
        else:
            severity = ErrorSeverity.MEDIUM
            category = ErrorCategory.SYSTEM
            resolution_suggestions = []

        # Create error report
        error_report = ErrorReport(
            error_id=error_id,
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            message=str(error),
            context=context or ErrorContext("unknown", "unknown"),
            exception_type=type(error).__name__,
            stack_trace=traceback.format_exc(),
            resolution_suggestions=resolution_suggestions
        )

        self.error_reports.append(error_report)

        # Log with appropriate level
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }[severity]

        log_message = self._format_error_message(error_report)
        self.logger.log(log_level, log_message)

        return error_report

    def _format_error_message(self, error_report: ErrorReport) -> str:
        """Format error message for logging"""
        return (
            f"[{error_report.error_id}] {error_report.category.value.upper()}: "
            f"{error_report.message} | "
            f"Component: {error_report.context.component} | "
            f"Operation: {error_report.context.operation}"
        )

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self.error_reports:
            return {"total_errors": 0}

        recent_errors = [
            err for err in self.error_reports
            if datetime.now() - err.timestamp < timedelta(hours=24)
        ]

        category_counts = {}
        severity_counts = {}

        for error in recent_errors:
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1

        return {
            "total_errors": len(self.error_reports),
            "recent_errors_24h": len(recent_errors),
            "category_distribution": category_counts,
            "severity_distribution": severity_counts,
            "error_rate": len(recent_errors) / 24  # errors per hour
        }


class RetryManager:
    """Advanced retry management with different strategies"""

    @staticmethod
    def network_retry(max_attempts: int = 3, base_delay: float = 1.0):
        """Retry decorator for network operations"""
        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=base_delay, min=1, max=30),
            retry=retry_if_exception_type((
                aiohttp.ClientError,
                requests.RequestException,
                NetworkError,
                asyncio.TimeoutError
            )),
            before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING)
        )

    @staticmethod
    def database_retry(max_attempts: int = 3):
        """Retry decorator for database operations"""
        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=10),
            retry=retry_if_exception_type((DatabaseError, ConnectionError)),
            before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING)
        )

    @staticmethod
    def rate_limit_retry(max_attempts: int = 5):
        """Retry decorator for rate-limited operations"""
        def should_retry(exception):
            if isinstance(exception, RateLimitError):
                return True
            if isinstance(exception, aiohttp.ClientResponseError):
                return exception.status in [429, 503]
            if isinstance(exception, requests.HTTPError):
                return exception.response.status_code in [429, 503]
            return False

        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=2, min=1, max=120),
            retry=should_retry,
            before_sleep=before_sleep_log(logging.getLogger(__name__), logging.INFO)
        )


class ErrorHandler:
    """Centralized error handling system"""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.error_handlers: Dict[Type[Exception], Callable] = {}
        self.setup_default_handlers()

    def setup_default_handlers(self):
        """Setup default error handlers"""
        self.register_handler(ValidationError, self._handle_validation_error)
        self.register_handler(NetworkError, self._handle_network_error)
        self.register_handler(DatabaseError, self._handle_database_error)
        self.register_handler(RateLimitError, self._handle_rate_limit_error)

    def register_handler(self, exception_type: Type[Exception], handler: Callable):
        """Register custom error handler"""
        self.error_handlers[exception_type] = handler

    def handle_error(self, error: Exception, context: Optional[ErrorContext] = None) -> ErrorReport:
        """Handle error with appropriate strategy"""
        error_report = self.logger.log_error(error, context)

        # Use specific handler if available
        handler = self.error_handlers.get(type(error))
        if handler:
            try:
                handler(error, error_report)
            except Exception as handler_error:
                self.logger.log_error(
                    CustomError(
                        f"Error in error handler: {handler_error}",
                        ErrorSeverity.HIGH,
                        ErrorCategory.SYSTEM
                    )
                )

        return error_report

    def _handle_validation_error(self, error: ValidationError, report: ErrorReport):
        """Handle validation errors"""
        report.resolution_suggestions.extend([
            "Check input data format and constraints",
            "Verify required fields are provided",
            "Review validation rules"
        ])

    def _handle_network_error(self, error: NetworkError, report: ErrorReport):
        """Handle network errors"""
        report.resolution_suggestions.extend([
            "Check internet connectivity",
            "Verify target URL is accessible",
            "Consider implementing exponential backoff",
            "Check for rate limiting"
        ])

    def _handle_database_error(self, error: DatabaseError, report: ErrorReport):
        """Handle database errors"""
        report.resolution_suggestions.extend([
            "Check database connection",
            "Verify database schema",
            "Review SQL query syntax",
            "Check database permissions"
        ])

    def _handle_rate_limit_error(self, error: RateLimitError, report: ErrorReport):
        """Handle rate limiting errors"""
        report.resolution_suggestions.extend([
            "Implement exponential backoff",
            "Reduce request frequency",
            "Consider using multiple API keys",
            "Implement request queuing"
        ])


def error_boundary(
    logger: Optional[StructuredLogger] = None,
    context: Optional[ErrorContext] = None,
    reraise: bool = True,
    default_return: Any = None
):
    """Decorator to create error boundaries around functions"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if logger:
                    logger.log_error(e, context)
                if reraise:
                    raise
                return default_return

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if logger:
                    logger.log_error(e, context)
                if reraise:
                    raise
                return default_return

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


class HealthChecker:
    """System health monitoring with error correlation"""

    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
        self.health_checks: Dict[str, Callable] = {}

    def register_health_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.health_checks[name] = check_func

    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks and correlate with errors"""
        results = {}

        for name, check_func in self.health_checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                results[name] = {"status": "healthy", "details": result}
            except Exception as e:
                self.error_handler.handle_error(
                    e, ErrorContext(f"health_check_{name}", "health_monitor")
                )
                results[name] = {"status": "unhealthy", "error": str(e)}

        # Add error statistics
        results["error_statistics"] = self.error_handler.logger.get_error_statistics()

        return results


# Global error handler instance
_global_logger = StructuredLogger("osint_system")
_global_error_handler = ErrorHandler(_global_logger)


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    return _global_error_handler


def get_logger() -> StructuredLogger:
    """Get global logger instance"""
    return _global_logger


# Convenience functions
def log_error(error: Exception, context: Optional[ErrorContext] = None) -> ErrorReport:
    """Convenience function to log error"""
    return _global_error_handler.handle_error(error, context)


def create_context(operation: str, component: str, **kwargs) -> ErrorContext:
    """Convenience function to create error context"""
    return ErrorContext(operation, component, additional_data=kwargs)