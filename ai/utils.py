"""
Utility functions for AI modules
Simple error handling and decorators
"""

import logging
import functools
from typing import Any, Callable

logger = logging.getLogger(__name__)

def simple_error_handler(func: Callable) -> Callable:
    """Simple error handler decorator for AI functions"""

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise

    # Check if function is async
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

class AIError(Exception):
    """Simple AI-specific error class"""
    pass
