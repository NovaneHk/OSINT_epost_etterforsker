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

# Future Phase 3 Connectors
try:
    from .spiderfoot_connector import SpiderFootConnector
except ImportError:
    SpiderFootConnector = None

try:
    from .reconng_connector import ReconNGConnector
except ImportError:
    ReconNGConnector = None

try:
    from .intelowl_connector import IntelOwlConnector
except ImportError:
    IntelOwlConnector = None

__all__ = [
    'BaseConnector',
    'TheHarvesterConnector',
    'HIBPConnector',
    'TheHarvesterEnhanced',
    'SpiderFootConnector',
    'ReconNGConnector',
    'IntelOwlConnector',
]
