#!/usr/bin/env python3
"""
Tests for Performance Monitoring
"""

import pytest
import time
import asyncio
from datetime import datetime, timedelta
from core.performance import PerformanceMonitor, PerformanceMetric

def test_performance_monitor_initialization():
    """Test performance monitor initialization"""
    monitor = PerformanceMonitor()
    assert monitor.metrics_history is not None
    assert monitor.active_timers == {}
    assert monitor.performance_thresholds is not None

def test_timer_operations():
    """Test timer start/stop operations"""
    monitor = PerformanceMonitor()
    
    # Start timer
    timer_id = monitor.start_timer("test_operation")
    assert timer_id in monitor.active_timers
    
    # Let some time pass
    time.sleep(0.1)
    
    # Stop timer
    duration = monitor.stop_timer(timer_id, "test_operation")
    assert duration > 0
    assert timer_id not in monitor.active_timers

def test_record_metric():
    """Test metric recording"""
    monitor = PerformanceMonitor()
    monitor.record_metric(
        'test_metric',
        value=42.0,
        unit='ms',
        category='testing'
    )
    
    # Check if metric was recorded
    assert 'test_metric' in monitor.metrics_history

def test_threshold_check():
    """Test performance threshold checking"""
    monitor = PerformanceMonitor()
    
    # Test within threshold
    metric = PerformanceMetric(
        name='memory_usage_mb',
        value=100.0,
        unit='MB',
        timestamp=datetime.now(),
        category='system'
    )
    assert monitor._check_threshold(metric)
    
        # Test above threshold
    metric = PerformanceMetric(
        name='memory_usage_mb',
        value=25000.0,  # 25GB - well above the 20GB threshold
        unit='MB',
        timestamp=datetime.now(),
        category='system'
    )
    assert not monitor._check_threshold(metric)

def test_metric_collection():
    """Test comprehensive metric collection"""
    monitor = PerformanceMonitor()
    monitor._collect_system_metrics()
    
    # Check if basic metrics were collected
    assert any('cpu_usage' in metric for metric in monitor.metrics_history.keys())
    assert any('memory' in metric for metric in monitor.metrics_history.keys())

def test_performance_metric_dataclass():
    """Test PerformanceMetric dataclass"""
    metric = PerformanceMetric(
        name='test',
        value=42.0,
        unit='ms',
        timestamp=datetime.now(),
        category='testing'
    )
    assert metric.name == 'test'
    assert metric.value == 42.0
    assert metric.unit == 'ms'
    assert metric.category == 'testing'

def test_metric_history_limits():
    """Test metric history size limits"""
    monitor = PerformanceMonitor()
    
    # Record many metrics
    for i in range(2000):
        monitor.record_metric(
            'test_metric',
            value=float(i),
            unit='count',
            category='testing'
        )
    
    # Check if history size is limited
    assert len(monitor.metrics_history['test_metric']) <= 1000

def test_background_monitoring():
    """Test background monitoring thread"""
    monitor = PerformanceMonitor()
    assert monitor._monitoring_active is True
    assert monitor._monitor_thread.is_alive()
    
    # Let the monitor run for a bit
    time.sleep(0.1)
    
    # Stop monitoring
    monitor._monitoring_active = False
    start_time = time.time()
    while monitor._monitor_thread.is_alive() and time.time() - start_time < 2.0:
        time.sleep(0.1)
    
    assert not monitor._monitor_thread.is_alive()

@pytest.mark.asyncio
async def test_async_performance_tracking():
    """Test async operation performance tracking"""
    monitor = PerformanceMonitor()
    
    async def test_operation():
        timer_id = monitor.start_timer("async_op")
        await asyncio.sleep(0.1)
        return monitor.stop_timer(timer_id, "async_op")
    
    duration = await test_operation()
    assert duration >= 0.1