"""
OSINT Integration Layer
Connectors for external OSINT tools and services
"""

from .base_connector import BaseConnector
from .theharvester_connector import TheHarvesterConnector
from .hibp_connector import HIBPConnector

# Phase 2 Enhanced Connectors
try:
    from .theharvester_enhanced import TheHarvesterEnhanced
except ImportError:
    TheHarvesterEnhanced = None

# Future Phase 3 Connectors (will be implemented)
# from .spiderfoot_connector import SpiderFootConnector
# from .reconng_connector import ReconNGConnector

__all__ = [
    'BaseConnector',
    'TheHarvesterConnector',
    'HIBPConnector',
    'TheHarvesterEnhanced'
]
