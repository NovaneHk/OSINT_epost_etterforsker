"""Memory management and cleanup utilities for AI Engine"""

import gc
import psutil
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def get_memory_usage() -> float:
    """Get current memory usage in percentage"""
    return psutil.Process().memory_percent()

def should_cleanup(threshold: float) -> bool:
    """Check if memory cleanup is needed"""
    return get_memory_usage() > threshold

def cleanup_memory():
    """Perform memory cleanup"""
    gc.collect()

class MemoryManager:
    """Memory management for AI operations"""
    
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
        self.operation_count = 0
        self.cleanup_interval = 100
        
    def check_memory(self):
        """Check memory usage and cleanup if needed"""
        self.operation_count += 1
        
        if (self.operation_count % self.cleanup_interval == 0 or 
            should_cleanup(self.threshold)):
            cleanup_memory()
            logger.info("Memory cleanup performed")
            
    def batch_size_for_operation(self, data_size: int, base_batch_size: int = 100) -> int:
        """Calculate optimal batch size based on memory conditions"""
        memory_usage = get_memory_usage()
        if memory_usage > self.threshold:
            # Reduce batch size when memory usage is high
            return max(1, base_batch_size // 2)
        return base_batch_size