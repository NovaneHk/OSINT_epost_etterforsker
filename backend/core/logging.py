"""
Logging Configuration
Structured logging setup for the OSINT backend
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any

from .config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """Configure application logging"""

    # Set log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(message)s | '
            'file:%(filename)s:%(lineno)d | func:%(funcName)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if settings.LOG_FILE:
        log_file_path = Path(settings.LOG_FILE)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Configure third-party loggers
    configure_third_party_loggers()

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {settings.LOG_LEVEL}")


def configure_third_party_loggers() -> None:
    """Configure logging levels for third-party packages"""

    # Reduce noise from third-party packages
    third_party_loggers = {
        'uvicorn.access': logging.WARNING,
        'httpx': logging.WARNING,
        'sqlalchemy.engine': logging.WARNING if not settings.DEBUG else logging.INFO,
        'aiohttp.access': logging.WARNING,
    }

    for logger_name, level in third_party_loggers.items():
        logging.getLogger(logger_name).setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance for a module"""
    return logging.getLogger(name)


class StructuredLogger:
    """Enhanced logger with structured logging capabilities"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def info(self, message: str, **kwargs):
        """Log info message with structured data"""
        extra_data = self._format_extra(kwargs)
        self.logger.info(f"{message} | {extra_data}" if extra_data else message)

    def warning(self, message: str, **kwargs):
        """Log warning message with structured data"""
        extra_data = self._format_extra(kwargs)
        self.logger.warning(f"{message} | {extra_data}" if extra_data else message)

    def error(self, message: str, **kwargs):
        """Log error message with structured data"""
        extra_data = self._format_extra(kwargs)
        self.logger.error(f"{message} | {extra_data}" if extra_data else message)

    def debug(self, message: str, **kwargs):
        """Log debug message with structured data"""
        extra_data = self._format_extra(kwargs)
        self.logger.debug(f"{message} | {extra_data}" if extra_data else message)

    def _format_extra(self, data: Dict[str, Any]) -> str:
        """Format extra data for logging"""
        if not data:
            return ""

        formatted_items = []
        for key, value in data.items():
            formatted_items.append(f"{key}={value}")

        return " | ".join(formatted_items)


def get_model_logger(name: str) -> logging.Logger:
    """Get logger for model modules"""
    return logging.getLogger(f"osint.models.{name}")


def get_api_logger(name: str) -> logging.Logger:
    """Get logger for API modules"""
    return logging.getLogger(f"osint.api.{name}")
