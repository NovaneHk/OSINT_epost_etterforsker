"""
Configuration Management System
Handles loading and managing YAML configuration files
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class SystemConfig:
    """System configuration data class."""
    default_persona: str = "technical_leaders"
    default_sector: str = "technology"
    default_geo: str = "nordics"
    rate_limit: float = 2.0
    max_concurrent: int = 10
    data_retention_days: int = 90
    gdpr_compliance_mode: bool = True

class ConfigManager:
    """Manages system configuration files and settings."""

    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.system_config = SystemConfig()
        self._ensure_config_files()

    def _ensure_config_files(self):
        """Ensure all required configuration files exist."""

        config_files = {
            'personas.yml': self._default_personas_config,
            'sources.yml': self._default_sources_config,
            'rules.yml': self._default_rules_config
        }

        for filename, default_content in config_files.items():
            config_path = self.config_dir / filename
            if not config_path.exists():
                logger.info(f"Creating default config file: {filename}")
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(default_content(), f, default_flow_style=False, allow_unicode=True)

    def load_personas(self) -> Dict[str, Any]:
        """Load personas configuration."""
        return self._load_yaml_config('personas.yml')

    def load_sources(self) -> Dict[str, Any]:
        """Load sources configuration."""
        return self._load_yaml_config('sources.yml')

    def load_rules(self) -> Dict[str, Any]:
        """Load processing rules configuration."""
        return self._load_yaml_config('rules.yml')

    def _load_yaml_config(self, filename: str) -> Dict[str, Any]:
        """Load a YAML configuration file."""

        config_path = self.config_dir / filename
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {filename}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {filename}: {e}")
            return {}

    def get_current_config(self) -> Dict[str, Any]:
        """Get current system configuration."""
        return {
            'system': self.system_config.__dict__,
            'personas': self.load_personas(),
            'sources': self.load_sources(),
            'rules': self.load_rules()
        }

    def update_config(self, updates: Dict[str, Any]):
        """Update system configuration."""
        for key, value in updates.items():
            if hasattr(self.system_config, key):
                setattr(self.system_config, key, value)
                logger.info(f"Updated config: {key} = {value}")

    def _default_personas_config(self) -> Dict[str, Any]:
        """Default personas configuration."""
        return {
            'personas': {
                'technical_leaders': {
                    'description': 'Technical decision makers and engineering leadership',
                    'roles': [
                        'CTO', 'Tech Lead', 'VP Engineering', 'Head of Technology',
                        'Technical Director', 'Chief Technology Officer'
                    ],
                    'email_patterns': [
                        'cto@', 'tech@', 'engineering@', 'dev@', 'technical@'
                    ],
                    'negative_signals': [
                        'intern', 'junior', 'assistant', 'coordinator'
                    ],
                    'scoring_weight': 40,
                    'priority_level': 'high'
                },
                'procurement_specialists': {
                    'description': 'Procurement, purchasing, and sourcing stakeholders',
                    'roles': [
                        'Procurement Manager', 'Purchasing Director',
                        'Supply Chain Manager', 'Buyer', 'Sourcing Manager'
                    ],
                    'email_patterns': [
                        'procurement@', 'purchasing@', 'sourcing@', 'buyer@', 'supply@'
                    ],
                    'negative_signals': [
                        'assistant', 'clerk', 'junior'
                    ],
                    'scoring_weight': 35,
                    'priority_level': 'high'
                },
                'operations_leaders': {
                    'description': 'Operations and execution-focused leadership roles',
                    'roles': [
                        'COO', 'Operations Manager', 'Head of Operations',
                        'VP Operations', 'Operations Director',
                        'CEO', 'Founder', 'Co-Founder', 'Managing Director'
                    ],
                    'email_patterns': [
                        'ops@', 'operations@', 'coo@', 'admin@'
                    ],
                    'negative_signals': [
                        'coordinator', 'assistant', 'clerk'
                    ],
                    'scoring_weight': 30,
                    'priority_level': 'medium'
                },
                'sales_leaders': {
                    'description': 'Commercial and revenue leadership roles',
                    'roles': [
                        'Sales Director', 'VP Sales', 'Head of Sales',
                        'Business Development', 'Revenue Operations'
                    ],
                    'email_patterns': [
                        'sales@', 'business@', 'bd@', 'revenue@'
                    ],
                    'negative_signals': [
                        'rep', 'junior', 'assistant'
                    ],
                    'scoring_weight': 25,
                    'priority_level': 'medium'
                }
            }
        }

    def _default_sources_config(self) -> Dict[str, Any]:
        """Default sources configuration."""
        return {
            'source_categories': {
                'directories': {
                    'priority': 1,
                    'daily_limit': 1000,
                    'sources': [
                        {
                            'name': 'Norwegian Chamber of Commerce',
                            'url': 'https://www.chamber.no/member-directory',
                            'type': 'static',
                            'company_selector': '.member-item',
                            'name_selector': '.company-name',
                            'contact_selector': '.contact-link',
                            'credibility_score': 95,
                            'enabled': True
                        },
                        {
                            'name': 'Nordic Tech Directory',
                            'url': 'https://nordictech.directory/companies',
                            'type': 'dynamic',
                            'wait_selector': '.company-grid',
                            'pagination': True,
                            'credibility_score': 85,
                            'enabled': True
                        }
                    ]
                },
                'events': {
                    'priority': 2,
                    'daily_limit': 500,
                    'sources': [
                        {
                            'name': 'TechCrunch Disrupt Exhibitors',
                            'url': 'https://techcrunch.com/events/disrupt/exhibitors',
                            'type': 'dynamic',
                            'credibility_score': 90,
                            'enabled': True
                        },
                        {
                            'name': 'Web Summit Startups',
                            'url': 'https://websummit.com/startups',
                            'type': 'static',
                            'credibility_score': 85,
                            'enabled': True
                        }
                    ]
                },
                'company_sites': {
                    'priority': 3,
                    'daily_limit': 2000,
                    'crawl_patterns': [
                        '/about', '/contact', '/team', '/press', '/investors'
                    ]
                }
            },
            'search_dorks': {
                'technology': [
                    'inurl:about-us "CTO" OR "technology"',
                    'site:crunchbase.com {geo} tech startup',
                    '"software company" {geo} contact',
                    'intitle:"team" "CTO" OR "tech lead" {geo}'
                ],
                'ecommerce': [
                    'powered by shopify {geo}',
                    'inurl:contact "e-commerce" OR "online store"',
                    '"webshop" OR "online retail" {geo}',
                    'site:shopify.com {geo} store'
                ],
                'manufacturing': [
                    '"manufacturing company" {geo} contact',
                    'intitle:"about us" manufacturing {geo}',
                    '"industrial" OR "production" {geo} team'
                ]
            }
        }

    def _default_rules_config(self) -> Dict[str, Any]:
        """Default processing rules configuration."""
        return {
            'processing_rules': {
                'rate_limiting': {
                    'requests_per_second': 2,
                    'max_concurrent': 10,
                    'retry_attempts': 3,
                    'backoff_multiplier': 2,
                    'respect_crawl_delay': True
                },
                'validation_thresholds': {
                    'min_confidence_score': 0.6,
                    'max_risk_score': 30,
                    'require_mx_validation': True,
                    'smtp_probe_enabled': False
                },
                'scoring_weights': {
                    'persona_match': 0.35,
                    'sector_relevance': 0.25,
                    'geographic_preference': 0.20,
                    'source_credibility': 0.15,
                    'data_freshness': 0.05
                },
                'filtering_rules': {
                    'exclude_consumer_domains': True,
                    'exclude_educational': True,
                    'exclude_government': False,
                    'min_company_size': 10,
                    'max_personal_email_ratio': 0.1
                }
            },
            'compliance_settings': {
                'data_retention_days': 90,
                'audit_logging': True,
                'gdpr_compliance_mode': True,
                'automatic_opt_out': True,
                'privacy_policy_url': 'https://yourcompany.com/privacy'
            },
            'geographic_targeting': {
                'nordics': {
                    'countries': ['NO', 'SE', 'DK', 'FI', 'IS'],
                    'languages': ['nb', 'sv', 'da', 'fi', 'is', 'en'],
                    'tld_preferences': ['.no', '.se', '.dk', '.fi', '.is'],
                    'scoring_boost': 20
                },
                'dach': {
                    'countries': ['DE', 'AT', 'CH'],
                    'languages': ['de', 'en'],
                    'tld_preferences': ['.de', '.at', '.ch'],
                    'scoring_boost': 15
                },
                'eu_core': {
                    'countries': ['FR', 'NL', 'BE', 'LU', 'IE'],
                    'languages': ['fr', 'nl', 'en'],
                    'tld_preferences': ['.fr', '.nl', '.be', '.eu'],
                    'scoring_boost': 10
                }
            },
            'sector_definitions': {
                'technology': {
                    'keywords': ['SaaS', 'software', 'tech', 'digital', 'cloud', 'AI'],
                    'negative_keywords': ['hardware', 'manufacturing'],
                    'size_indicators': ['startup', 'scale-up', 'enterprise'],
                    'scoring_multiplier': 1.5
                },
                'ecommerce': {
                    'keywords': ['e-commerce', 'retail', 'online store', 'webshop'],
                    'technology_signals': ['Shopify', 'WooCommerce', 'Magento'],
                    'size_indicators': ['GMV', 'orders', 'customers'],
                    'scoring_multiplier': 1.3
                },
                'manufacturing': {
                    'keywords': ['manufacturing', 'production', 'industrial'],
                    'exclusions': ['retail', 'service'],
                    'size_indicators': ['employees', 'facilities', 'revenue'],
                    'scoring_multiplier': 1.0
                }
            }
        }