"""
Enhanced Performance Monitoring Module for Phase 1
Comprehensive performance optimization and monitoring
"""

import time
import psutil
import logging
import sqlite3
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
import gc
import tracemalloc
from dataclasses import dataclass
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    category: str
    metadata: Dict[str, Any] = None

class PerformanceMonitor:
    """Comprehensive performance monitoring and optimization."""

    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.active_timers = {}
        self.performance_thresholds = {
            'response_time_ms': 2000,
            'memory_usage_mb': 512,
            'cpu_usage_percent': 80,
            'database_query_ms': 1000,
            'email_extraction_rate': 1.0,  # emails per second
            'validation_rate': 10.0  # validations per second
        }

        # Start background monitoring
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(target=self._background_monitor, daemon=True)
        self._monitor_thread.start()

        # Initialize tracemalloc for memory profiling
        if not tracemalloc.is_tracing():
            tracemalloc.start()

    def _background_monitor(self):
        """Background thread for continuous monitoring."""
        while self._monitoring_active:
            try:
                # Collect system metrics
                self._collect_system_metrics()

                # Sleep for 30 seconds
                time.sleep(30)

            except Exception as e:
                logger.error(f"Background monitoring error: {e}")
                time.sleep(60)  # Wait longer on error

    def _collect_system_metrics(self):
        """Collect system performance metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_metric('cpu_usage_percent', cpu_percent, 'percent', 'system')

            # Memory metrics
            memory = psutil.virtual_memory()
            memory_mb = memory.used / (1024 * 1024)
            self.record_metric('memory_usage_mb', memory_mb, 'MB', 'system')
            self.record_metric('memory_percent', memory.percent, 'percent', 'system')

            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.record_metric('disk_usage_percent', disk_percent, 'percent', 'system')

            # Process-specific metrics
            process = psutil.Process()
            process_memory = process.memory_info().rss / (1024 * 1024)
            self.record_metric('process_memory_mb', process_memory, 'MB', 'process')

            # Python memory tracking
            if tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                self.record_metric('python_memory_current_mb', current / (1024 * 1024), 'MB', 'python')
                self.record_metric('python_memory_peak_mb', peak / (1024 * 1024), 'MB', 'python')

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")

    def record_metric(self, name: str, value: float, unit: str, category: str, metadata: Dict[str, Any] = None):
        """Record a performance metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            category=category,
            metadata=metadata or {}
        )

        self.metrics_history[name].append(metric)

        # Check thresholds
        self._check_threshold(metric)

    def _check_threshold(self, metric: PerformanceMetric):
        """Check if metric exceeds performance thresholds."""
        threshold = self.performance_thresholds.get(metric.name)
        if threshold and metric.value > threshold:
            logger.warning(
                f"Performance threshold exceeded: {metric.name} = {metric.value} {metric.unit} "
                f"(threshold: {threshold} {metric.unit})"
            )

    def timer(self, name: str, category: str = 'operation'):
        """Decorator for timing function execution."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.time()
                    duration_ms = (end_time - start_time) * 1000
                    self.record_metric(
                        f"{name}_duration_ms",
                        duration_ms,
                        'ms',
                        category,
                        {'function': func.__name__}
                    )
            return wrapper
        return decorator

    def start_timer(self, name: str) -> str:
        """Start a named timer."""
        timer_id = f"{name}_{int(time.time() * 1000)}"
        self.active_timers[timer_id] = time.time()
        return timer_id

    def stop_timer(self, timer_id: str, category: str = 'operation') -> float:
        """Stop a named timer and record the metric."""
        if timer_id not in self.active_timers:
            logger.warning(f"Timer {timer_id} not found")
            return 0.0

        start_time = self.active_timers.pop(timer_id)
        duration_ms = (time.time() - start_time) * 1000

        # Extract name from timer_id
        name = timer_id.rsplit('_', 1)[0]
        self.record_metric(f"{name}_duration_ms", duration_ms, 'ms', category)

        return duration_ms

    def measure_database_performance(self, db_path: str) -> Dict[str, Any]:
        """Measure database performance metrics."""
        metrics = {}

        try:
            # Connection time
            start_time = time.time()
            with sqlite3.connect(db_path) as conn:
                connection_time = (time.time() - start_time) * 1000
                metrics['connection_time_ms'] = connection_time

                cursor = conn.cursor()

                # Query performance tests
                test_queries = [
                    ("SELECT COUNT(*) FROM companies", "companies_count"),
                    ("SELECT COUNT(*) FROM emails", "emails_count"),
                    ("SELECT COUNT(*) FROM companies WHERE retrieved_at > datetime('now', '-24 hours')", "recent_companies"),
                    ("SELECT AVG(confidence_score) FROM emails WHERE validation_status = 'valid'", "avg_confidence")
                ]

                for query, metric_name in test_queries:
                    start_time = time.time()
                    try:
                        cursor.execute(query)
                        result = cursor.fetchone()
                        query_time = (time.time() - start_time) * 1000

                        metrics[f"{metric_name}_query_time_ms"] = query_time
                        metrics[f"{metric_name}_result"] = result[0] if result else 0

                        self.record_metric(
                            f"db_{metric_name}_query_ms",
                            query_time,
                            'ms',
                            'database'
                        )

                    except Exception as e:
                        logger.error(f"Database query error for {metric_name}: {e}")
                        metrics[f"{metric_name}_error"] = str(e)

                # Database size
                db_size = Path(db_path).stat().st_size / (1024 * 1024)  # MB
                metrics['database_size_mb'] = db_size

                self.record_metric('database_size_mb', db_size, 'MB', 'database')

        except Exception as e:
            logger.error(f"Database performance measurement error: {e}")
            metrics['error'] = str(e)

        return metrics

    def measure_email_processing_performance(self, sample_emails: List[str]) -> Dict[str, Any]:
        """Measure email processing performance."""
        if not sample_emails:
            return {'error': 'No sample emails provided'}

        metrics = {}

        try:
            # Email validation performance
            start_time = time.time()
            valid_count = 0

            for email in sample_emails:
                # Simple email validation (placeholder)
                if '@' in email and '.' in email.split('@')[1]:
                    valid_count += 1

            processing_time = time.time() - start_time
            emails_per_second = len(sample_emails) / processing_time if processing_time > 0 else 0

            metrics.update({
                'total_emails': len(sample_emails),
                'valid_emails': valid_count,
                'processing_time_seconds': processing_time,
                'emails_per_second': emails_per_second,
                'validation_accuracy': valid_count / len(sample_emails) if sample_emails else 0
            })

            self.record_metric('email_processing_rate', emails_per_second, 'emails/sec', 'processing')

        except Exception as e:
            logger.error(f"Email processing performance measurement error: {e}")
            metrics['error'] = str(e)

        return metrics

    def optimize_memory_usage(self) -> Dict[str, Any]:
        """Optimize memory usage and return metrics."""
        optimization_results = {}

        try:
            # Get memory before optimization
            if tracemalloc.is_tracing():
                before_memory, _ = tracemalloc.get_traced_memory()
                optimization_results['memory_before_mb'] = before_memory / (1024 * 1024)

            # Force garbage collection
            collected = gc.collect()
            optimization_results['objects_collected'] = collected

            # Get memory after optimization
            if tracemalloc.is_tracing():
                after_memory, _ = tracemalloc.get_traced_memory()
                optimization_results['memory_after_mb'] = after_memory / (1024 * 1024)
                optimization_results['memory_freed_mb'] = (before_memory - after_memory) / (1024 * 1024)

            # Clear old metrics to free memory
            cutoff_time = datetime.now() - timedelta(hours=24)
            for metric_name, history in self.metrics_history.items():
                # Keep only recent metrics
                while history and history[0].timestamp < cutoff_time:
                    history.popleft()

            optimization_results['metrics_cleaned'] = True

            logger.info(f"Memory optimization completed: {optimization_results}")

        except Exception as e:
            logger.error(f"Memory optimization error: {e}")
            optimization_results['error'] = str(e)

        return optimization_results

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'metrics_collected': len(self.metrics_history),
            'active_timers': len(self.active_timers),
            'categories': {},
            'recent_metrics': {},
            'performance_status': 'healthy'
        }

        try:
            # Categorize metrics
            for metric_name, history in self.metrics_history.items():
                if not history:
                    continue

                latest_metric = history[-1]
                category = latest_metric.category

                if category not in summary['categories']:
                    summary['categories'][category] = {
                        'metric_count': 0,
                        'latest_values': {}
                    }

                summary['categories'][category]['metric_count'] += 1
                summary['categories'][category]['latest_values'][metric_name] = {
                    'value': latest_metric.value,
                    'unit': latest_metric.unit,
                    'timestamp': latest_metric.timestamp.isoformat()
                }

                # Add to recent metrics
                summary['recent_metrics'][metric_name] = {
                    'current': latest_metric.value,
                    'unit': latest_metric.unit,
                    'trend': self._calculate_trend(history)
                }

                # Check performance status
                threshold = self.performance_thresholds.get(metric_name)
                if threshold and latest_metric.value > threshold:
                    summary['performance_status'] = 'degraded'

            # Calculate averages for key metrics
            key_metrics = ['cpu_usage_percent', 'memory_usage_mb', 'response_time_ms']
            for metric_name in key_metrics:
                if metric_name in self.metrics_history:
                    history = self.metrics_history[metric_name]
                    if history:
                        recent_values = [m.value for m in list(history)[-10:]]  # Last 10 values
                        summary['recent_metrics'][f"{metric_name}_avg"] = {
                            'value': sum(recent_values) / len(recent_values),
                            'unit': history[-1].unit,
                            'sample_size': len(recent_values)
                        }

        except Exception as e:
            logger.error(f"Error generating performance summary: {e}")
            summary['error'] = str(e)

        return summary

    def _calculate_trend(self, history: deque) -> str:
        """Calculate trend for metric history."""
        if len(history) < 2:
            return 'stable'

        recent_values = [m.value for m in list(history)[-5:]]  # Last 5 values
        if len(recent_values) < 2:
            return 'stable'

        # Simple trend calculation
        first_half = sum(recent_values[:len(recent_values)//2])
        second_half = sum(recent_values[len(recent_values)//2:])

        if second_half > first_half * 1.1:
            return 'increasing'
        elif second_half < first_half * 0.9:
            return 'decreasing'
        else:
            return 'stable'

    def benchmark_system(self) -> Dict[str, Any]:
        """Run comprehensive system benchmark."""
        benchmark_results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {}
        }

        try:
            # CPU benchmark
            start_time = time.time()
            # Simple CPU-intensive task
            result = sum(i * i for i in range(100000))
            cpu_time = time.time() - start_time
            benchmark_results['tests']['cpu_benchmark'] = {
                'duration_ms': cpu_time * 1000,
                'operations_per_second': 100000 / cpu_time if cpu_time > 0 else 0
            }

            # Memory allocation benchmark
            start_time = time.time()
            test_data = [i for i in range(50000)]
            memory_time = time.time() - start_time
            del test_data
            benchmark_results['tests']['memory_benchmark'] = {
                'duration_ms': memory_time * 1000,
                'allocations_per_second': 50000 / memory_time if memory_time > 0 else 0
            }

            # File I/O benchmark
            test_file = Path("data/.performance_test")
            test_file.parent.mkdir(exist_ok=True)

            start_time = time.time()
            with open(test_file, 'w') as f:
                for i in range(1000):
                    f.write(f"Test line {i}\n")

            with open(test_file, 'r') as f:
                lines = f.readlines()

            io_time = time.time() - start_time
            test_file.unlink(missing_ok=True)

            benchmark_results['tests']['io_benchmark'] = {
                'duration_ms': io_time * 1000,
                'lines_processed': len(lines),
                'lines_per_second': len(lines) / io_time if io_time > 0 else 0
            }

            # Overall performance score (simple calculation)
            cpu_score = min(100, 1000 / (cpu_time * 1000))  # Higher is better
            memory_score = min(100, 1000 / (memory_time * 1000))
            io_score = min(100, 1000 / (io_time * 1000))

            benchmark_results['overall_score'] = (cpu_score + memory_score + io_score) / 3
            benchmark_results['performance_grade'] = self._get_performance_grade(benchmark_results['overall_score'])

        except Exception as e:
            logger.error(f"Benchmark error: {e}")
            benchmark_results['error'] = str(e)

        return benchmark_results

    def _get_performance_grade(self, score: float) -> str:
        """Get performance grade based on score."""
        if score >= 80:
            return 'A'
        elif score >= 60:
            return 'B'
        elif score >= 40:
            return 'C'
        elif score >= 20:
            return 'D'
        else:
            return 'F'

    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': self.get_performance_summary(),
            'benchmark': self.benchmark_system(),
            'recommendations': []
        }

        try:
            # Add database performance if available
            db_path = "data/osint_cache.db"
            if Path(db_path).exists():
                report['database_performance'] = self.measure_database_performance(db_path)

            # Generate recommendations
            summary = report['summary']

            # CPU recommendations
            if 'cpu_usage_percent' in summary['recent_metrics']:
                cpu_usage = summary['recent_metrics']['cpu_usage_percent']['current']
                if cpu_usage > 80:
                    report['recommendations'].append({
                        'type': 'cpu',
                        'priority': 'high',
                        'message': f'High CPU usage detected ({cpu_usage:.1f}%). Consider optimizing algorithms or reducing concurrent operations.'
                    })

            # Memory recommendations
            if 'memory_usage_mb' in summary['recent_metrics']:
                memory_usage = summary['recent_metrics']['memory_usage_mb']['current']
                if memory_usage > 512:
                    report['recommendations'].append({
                        'type': 'memory',
                        'priority': 'medium',
                        'message': f'High memory usage detected ({memory_usage:.1f} MB). Consider running memory optimization.'
                    })

            # Performance grade recommendations
            if 'overall_score' in report['benchmark']:
                score = report['benchmark']['overall_score']
                if score < 60:
                    report['recommendations'].append({
                        'type': 'performance',
                        'priority': 'high',
                        'message': f'Low performance score ({score:.1f}). System may need optimization or hardware upgrade.'
                    })

        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            report['error'] = str(e)

        return report

    def cleanup(self):
        """Cleanup monitoring resources."""
        self._monitoring_active = False
        if self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)

        if tracemalloc.is_tracing():
            tracemalloc.stop()


class DatabaseOptimizer:
    """Database performance optimization utilities."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def optimize_database(self) -> Dict[str, Any]:
        """Optimize database performance."""
        results = {
            'timestamp': datetime.now().isoformat(),
            'optimizations': []
        }

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Analyze database
                cursor.execute("ANALYZE")
                results['optimizations'].append('Database analysis completed')

                # Vacuum database
                cursor.execute("VACUUM")
                results['optimizations'].append('Database vacuum completed')

                # Create indexes if they don't exist
                indexes = [
                    ("idx_companies_retrieved_at", "CREATE INDEX IF NOT EXISTS idx_companies_retrieved_at ON companies(retrieved_at)"),
                    ("idx_emails_validation_status", "CREATE INDEX IF NOT EXISTS idx_emails_validation_status ON emails(validation_status)"),
                    ("idx_emails_company_id", "CREATE INDEX IF NOT EXISTS idx_emails_company_id ON emails(company_id)"),
                    ("idx_companies_sector", "CREATE INDEX IF NOT EXISTS idx_companies_sector ON companies(sector)")
                ]

                for index_name, index_sql in indexes:
                    cursor.execute(index_sql)
                    results['optimizations'].append(f'Index {index_name} created/verified')

                # Update statistics
                cursor.execute("PRAGMA optimize")
                results['optimizations'].append('Database statistics updated')

                conn.commit()

        except Exception as e:
            logger.error(f"Database optimization error: {e}")
            results['error'] = str(e)

        return results

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {}

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Table sizes
                tables = ['companies', 'emails', 'audit_log', 'cache', 'seeds']
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        stats[f"{table}_count"] = count
                    except sqlite3.OperationalError:
                        stats[f"{table}_count"] = 0

                # Database file size
                db_size = Path(self.db_path).stat().st_size
                stats['database_size_bytes'] = db_size
                stats['database_size_mb'] = db_size / (1024 * 1024)

                # Page info
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]

                stats['page_count'] = page_count
                stats['page_size'] = page_size
                stats['total_pages_size_mb'] = (page_count * page_size) / (1024 * 1024)

        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            stats['error'] = str(e)

        return stats
