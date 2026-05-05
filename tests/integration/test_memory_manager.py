"""Tests for AI memory management"""

import pytest
from ai.memory_manager import MemoryManager, get_memory_usage, should_cleanup
import psutil

def test_memory_manager_initialization():
    """Test memory manager initialization"""
    manager = MemoryManager(threshold=0.8)
    assert manager.threshold == 0.8
    assert manager.operation_count == 0
    assert manager.cleanup_interval == 100

def test_memory_usage_check():
    """Test memory usage checking"""
    usage = get_memory_usage()
    assert isinstance(usage, float)
    assert 0 <= usage <= 100.0

def test_cleanup_threshold():
    """Test cleanup threshold checking"""
    result = should_cleanup(threshold=100.0)  # Set high to ensure no cleanup
    assert result is False

def test_batch_size_calculation():
    """Test batch size calculation based on memory conditions"""
    manager = MemoryManager(threshold=0.8)
    base_size = 100
    
    # Test normal conditions
    batch_size = manager.batch_size_for_operation(data_size=1000, base_batch_size=base_size)
    assert isinstance(batch_size, int)
    assert batch_size > 0
    
    # Test minimum batch size
    batch_size = manager.batch_size_for_operation(data_size=10, base_batch_size=1)
    assert batch_size >= 1

def test_memory_check_operation():
    """Test memory check operation counting"""
    manager = MemoryManager(threshold=0.8)
    initial_count = manager.operation_count
    
    # Perform some operations
    for _ in range(50):
        manager.check_memory()
    
    assert manager.operation_count == initial_count + 50

def test_memory_cleanup_interval():
    """Test memory cleanup on interval"""
    manager = MemoryManager(threshold=0.8)
    manager.cleanup_interval = 10  # Set small interval for testing
    
    # This should trigger cleanup
    for _ in range(10):
        manager.check_memory()
    
    assert manager.operation_count == 10

def test_memory_usage_monitoring():
    """Test memory usage monitoring"""
    current_process = psutil.Process()
    initial_memory = current_process.memory_percent()
    
    # Create some memory pressure
    data = [i for i in range(1000000)]
    
    current_memory = current_process.memory_percent()
    assert current_memory >= initial_memory
    
    # Cleanup
    del data