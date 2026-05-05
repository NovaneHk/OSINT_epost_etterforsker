#!/usr/bin/env python3
"""
Test AI utilities
Tests error handling and decorators
"""

import pytest
import asyncio
from ai.utils import simple_error_handler, AIError

def test_sync_error_handler():
    """Test synchronous error handler"""
    
    @simple_error_handler
    def failing_function():
        raise ValueError("Test error")
    
    with pytest.raises(ValueError):
        failing_function()

@pytest.mark.asyncio
async def test_async_error_handler():
    """Test asynchronous error handler"""
    
    @simple_error_handler
    async def failing_async_function():
        raise ValueError("Test async error")
    
    with pytest.raises(ValueError):
        await failing_async_function()

def test_ai_error():
    """Test AIError exception"""
    with pytest.raises(AIError):
        raise AIError("Test AI error")

def test_successful_sync_function():
    """Test successful synchronous function execution"""
    
    @simple_error_handler
    def successful_function():
        return "success"
    
    assert successful_function() == "success"

@pytest.mark.asyncio
async def test_successful_async_function():
    """Test successful asynchronous function execution"""
    
    @simple_error_handler
    async def successful_async_function():
        return "async success"
    
    result = await successful_async_function()
    assert result == "async success"