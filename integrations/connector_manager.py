"""
Enhanced Connector Manager for Phase 2
Orchestration layer for all OSINT tool integrations
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional, Type
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import importlib
import inspect

from core.security import SecurityManager
from core.performance import PerformanceMonitor
from core.error_handling import OSINTError, handle_errors

logger = logging.getLogger(__name__)

class ConnectorStatus(Enum):
    """Connector status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"

@dataclass
class OSINTResult:
    """Standardized OSINT result structure"""
    source: str
    data_type: str
    content: Dict[str, Any]
    confidence: float
    timestamp: datetime
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

@dataclass
class ConnectorMetrics:
    """Connector performance metrics"""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    average_response_time: float = 0.0
    last_query_time: Optional[datetime] = None
    uptime_percentage: float = 100.0

class ConnectorManager:
    """Advanced connector management and orchestration"""

    def __init__(self, config_manager=None, security_manager=None, performance_monitor=None):
        self.config_manager = config_manager
        self.security_manager = security_manager or SecurityManager()
        self.performance_monitor = performance_monitor or PerformanceMonitor()

        # Connector registry
        self.connectors: Dict[str, Any] = {}
        self.connector_configs: Dict[str, Dict] = {}
        self.connector_status: Dict[str, ConnectorStatus] = {}
        self.connector_metrics: Dict[str, ConnectorMetrics] = {}

        # Load configuration
        self._load_connector_configs()

        # Initialize connectors
        self._initialize_connectors()

        logger.info(f"ConnectorManager initialized with {len(self.connectors)} connectors")

    def _load_connector_configs(self):
        """Load connector configurations from files"""
        try:
            config_path = Path("configs/connectors.yml")
            if config_path.exists():
                import yaml
                with open(config_path, 'r') as f:
                    configs = yaml.safe_load(f)
                    self.connector_configs = configs.get('connectors', {})
            else:
                # Default configurations
                self.connector_configs = {
                    'theharvester': {
                        'enabled': True,
                        'timeout': 30,
                        'max_retries': 3,
                        'sources': ['google', 'bing', 'linkedin']
                    },
                    'hibp': {
                        'enabled': True,
                        'api_key': None,
                        'timeout': 10,
                        'rate_limit': 1.5  # seconds between requests
                    },
                    'spiderfoot': {
                        'enabled': False,  # Requires installation
                        'api_url': 'http://localhost:5001',
                        'timeout': 60
                    }
                }

        except Exception as e:
            logger.error(f"Error loading connector configs: {e}")
            self.connector_configs = {}

    def _initialize_connectors(self):
        """Initialize all available connectors"""
        connector_modules = [
            'theharvester_connector',
            'hibp_connector',
            'spiderfoot_connector',
            'reconng_connector',
            'intelowl_connector',
            # Wave 4
            'metagoofil_connector',
            'pwndb_connector',
            'novanexus_connector',
        ]

        for module_name in connector_modules:
            try:
                self._load_connector(module_name)
            except Exception as e:
                logger.warning(f"Could not load connector {module_name}: {e}")

    def _load_connector(self, module_name: str):
        """Load a specific connector module"""
        try:
            # Import the connector module
            module = importlib.import_module(f'integrations.{module_name}')

            # Find connector class (should inherit from BaseConnector)
            connector_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    hasattr(obj, '__bases__') and
                    any('BaseConnector' in str(base) for base in obj.__bases__)):
                    connector_class = obj
                    break

            if connector_class:
                # Get configuration for this connector
                connector_name = module_name.replace('_connector', '')
                config = self.connector_configs.get(connector_name, {})

                if config.get('enabled', False):
                    # Initialize connector
                    connector = connector_class(config)

                    # Validate configuration
                    if connector.validate_config():
                        self.connectors[connector_name] = connector
                        self.connector_status[connector_name] = ConnectorStatus.ACTIVE
                        self.connector_metrics[connector_name] = ConnectorMetrics()
                        logger.info(f"Loaded connector: {connector_name}")
                    else:
                        logger.error(f"Invalid configuration for connector: {connector_name}")
                        self.connector_status[connector_name] = ConnectorStatus.ERROR
                else:
                    logger.info(f"Connector {connector_name} is disabled")
                    self.connector_status[connector_name] = ConnectorStatus.INACTIVE
            else:
                logger.error(f"No valid connector class found in {module_name}")

        except ImportError as e:
            logger.warning(f"Connector module {module_name} not found: {e}")
        except Exception as e:
            logger.error(f"Error loading connector {module_name}: {e}")

    @handle_errors
    async def search(self, connector_name: str, query: str, **kwargs) -> List[OSINTResult]:
        """Execute search using specified connector"""
        if connector_name not in self.connectors:
            raise OSINTError(f"Connector {connector_name} not available")

        connector = self.connectors[connector_name]
        metrics = self.connector_metrics[connector_name]

        # Security validation
        validation_result = self.security_manager.validate_input(query, "search_query")
        if not validation_result['is_valid']:
            raise OSINTError(f"Invalid query: {validation_result['threats_detected']}")

        # Performance monitoring
        timer_id = self.performance_monitor.start_timer(f"connector_{connector_name}_search")

        try:
            # Update metrics
            metrics.total_queries += 1
            metrics.last_query_time = datetime.now()

            # Execute search
            results = await connector.search(query, **kwargs)

            # Update success metrics
            metrics.successful_queries += 1

            # Record performance
            duration = self.performance_monitor.stop_timer(timer_id, 'connector')
            self._update_response_time(connector_name, duration)

            # Log successful search
            logger.info(f"Connector {connector_name} returned {len(results)} results for query: {query[:50]}...")

            return results

        except Exception as e:
            # Update failure metrics
            metrics.failed_queries += 1
            self.connector_status[connector_name] = ConnectorStatus.ERROR

            logger.error(f"Connector {connector_name} search failed: {e}")
            raise OSINTError(f"Search failed for {connector_name}: {str(e)}")

    async def search_all(self, query: str, enabled_connectors: Optional[List[str]] = None, **kwargs) -> Dict[str, List[OSINTResult]]:
        """Execute search across multiple connectors"""
        if enabled_connectors is None:
            enabled_connectors = [name for name, status in self.connector_status.items()
                                 if status == ConnectorStatus.ACTIVE]

        results = {}
        tasks = []

        # Create search tasks for all enabled connectors
        for connector_name in enabled_connectors:
            if connector_name in self.connectors:
                task = asyncio.create_task(
                    self.search(connector_name, query, **kwargs),
                    name=f"search_{connector_name}"
                )
                tasks.append((connector_name, task))

        # Execute searches concurrently
        for connector_name, task in tasks:
            try:
                connector_results = await task
                results[connector_name] = connector_results
            except Exception as e:
                logger.error(f"Search failed for {connector_name}: {e}")
                results[connector_name] = []

        return results

    def _update_response_time(self, connector_name: str, duration_ms: float):
        """Update average response time for connector"""
        metrics = self.connector_metrics[connector_name]

        if metrics.average_response_time == 0:
            metrics.average_response_time = duration_ms
        else:
            # Calculate moving average
            metrics.average_response_time = (metrics.average_response_time * 0.8) + (duration_ms * 0.2)

    def get_connector_status(self, connector_name: Optional[str] = None) -> Dict[str, Any]:
        """Get status information for connectors"""
        if connector_name:
            if connector_name not in self.connectors:
                return {'error': f'Connector {connector_name} not found'}

            return {
                'name': connector_name,
                'status': self.connector_status[connector_name].value,
                'metrics': asdict(self.connector_metrics[connector_name]),
                'capabilities': self.connectors[connector_name].get_capabilities(),
                'config': self.connector_configs.get(connector_name, {})
            }
        else:
            # Return status for all connectors
            status_info = {}
            for name in self.connectors:
                status_info[name] = self.get_connector_status(name)
            return status_info

    def get_available_connectors(self) -> List[str]:
        """Get list of available connector names"""
        return list(self.connectors.keys())

    def get_active_connectors(self) -> List[str]:
        """Get list of active connector names"""
        return [name for name, status in self.connector_status.items()
                if status == ConnectorStatus.ACTIVE]

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all connectors"""
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'connectors': {}
        }

        for connector_name, connector in self.connectors.items():
            try:
                # Perform basic health check
                if hasattr(connector, 'health_check'):
                    connector_health = await connector.health_check()
                else:
                    # Basic connectivity test
                    test_results = await self.search(connector_name, "test", limit=1)
                    connector_health = {'status': 'healthy', 'test_results': len(test_results)}

                health_status['connectors'][connector_name] = {
                    'status': 'healthy',
                    'details': connector_health,
                    'metrics': asdict(self.connector_metrics[connector_name])
                }

            except Exception as e:
                health_status['connectors'][connector_name] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'metrics': asdict(self.connector_metrics[connector_name])
                }
                health_status['overall_status'] = 'degraded'

        return health_status

    def enable_connector(self, connector_name: str) -> bool:
        """Enable a specific connector"""
        if connector_name in self.connectors:
            self.connector_status[connector_name] = ConnectorStatus.ACTIVE
            logger.info(f"Enabled connector: {connector_name}")
            return True
        return False

    def disable_connector(self, connector_name: str) -> bool:
        """Disable a specific connector"""
        if connector_name in self.connectors:
            self.connector_status[connector_name] = ConnectorStatus.INACTIVE
            logger.info(f"Disabled connector: {connector_name}")
            return True
        return False

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics for all connectors"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'total_connectors': len(self.connectors),
            'active_connectors': len(self.get_active_connectors()),
            'connector_metrics': {}
        }

        for connector_name, connector_metrics in self.connector_metrics.items():
            metrics['connector_metrics'][connector_name] = {
                **asdict(connector_metrics),
                'success_rate': (connector_metrics.successful_queries / max(connector_metrics.total_queries, 1)) * 100,
                'status': self.connector_status[connector_name].value
            }

        return metrics

    async def correlate_results(self, results: Dict[str, List[OSINTResult]]) -> List[OSINTResult]:
        """Correlate and deduplicate results from multiple connectors"""
        all_results = []
        seen_content = set()

        for connector_name, connector_results in results.items():
            for result in connector_results:
                # Create a hash of the content for deduplication
                content_hash = hash(json.dumps(result.content, sort_keys=True))

                if content_hash not in seen_content:
                    seen_content.add(content_hash)

                    # Enhance result with correlation metadata
                    result.metadata['correlation_id'] = content_hash
                    result.metadata['source_connector'] = connector_name

                    all_results.append(result)

        # Sort by confidence score (descending)
        all_results.sort(key=lambda x: x.confidence, reverse=True)

        return all_results

    def cleanup(self):
        """Cleanup connector resources"""
        for connector_name, connector in self.connectors.items():
            try:
                if hasattr(connector, 'cleanup'):
                    connector.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up connector {connector_name}: {e}")

        logger.info("ConnectorManager cleanup completed")


# Global connector manager instance
_connector_manager = None

def get_connector_manager() -> ConnectorManager:
    """Get global connector manager instance"""
    global _connector_manager
    if _connector_manager is None:
        _connector_manager = ConnectorManager()
    return _connector_manager
