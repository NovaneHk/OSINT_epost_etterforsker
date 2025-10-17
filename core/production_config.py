"""
Production Configuration Manager
Handles production-specific configuration including PostgreSQL, GDPR compliance, and security settings
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProductionConfig:
    """Production configuration data class."""
    profile: str = "prod"

    # Crawling configuration
    crawl_workers: int = 8
    crawl_sources: list = None
    crawl_retry_backoff_s: int = 2
    crawl_max_retries: int = 3
    crawl_user_agent_pool: str = "default"

    # Database configuration
    db_engine: str = "postgres"
    db_dsn: str = "postgresql://osint:osint@db:5432/osint"

    # Validation configuration
    validation_mx_check: bool = True
    validation_smtp_check: bool = False

    # Export configuration
    export_format: str = "csv"
    export_path: str = "out/leads.csv"

    # GDPR compliance
    gdpr_require_consent: bool = True
    gdpr_mask_unconsented: bool = True
    gdpr_retention_days: int = 365

    # Security settings
    security_pii_encrypt_at_rest: bool = True
    security_audit_log: bool = True

    def __post_init__(self):
        if self.crawl_sources is None:
            self.crawl_sources = ["directories", "events"]

class ProductionConfigManager:
    """Manages production configuration files and settings."""

    def __init__(self, config_file: str = "config.prod.yml"):
        self.config_file = Path(config_file)
        self.config = ProductionConfig()
        self.load_config()

    def load_config(self) -> None:
        """Load production configuration from YAML file."""
        if not self.config_file.exists():
            logger.warning(f"Production config file not found: {self.config_file}")
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}

            self._apply_config(config_data)
            logger.info(f"Loaded production configuration from {self.config_file}")

        except yaml.YAMLError as e:
            logger.error(f"Error parsing production config YAML: {e}")
        except Exception as e:
            logger.error(f"Error loading production config: {e}")

    def _apply_config(self, config_data: Dict[str, Any]) -> None:
        """Apply configuration data to the config object."""

        # Profile
        if 'profile' in config_data:
            self.config.profile = config_data['profile']

        # Crawling configuration
        if 'crawl' in config_data:
            crawl_config = config_data['crawl']
            if 'workers' in crawl_config:
                self.config.crawl_workers = crawl_config['workers']
            if 'sources' in crawl_config:
                self.config.crawl_sources = crawl_config['sources']
            if 'retry_backoff_s' in crawl_config:
                self.config.crawl_retry_backoff_s = crawl_config['retry_backoff_s']
            if 'max_retries' in crawl_config:
                self.config.crawl_max_retries = crawl_config['max_retries']
            if 'user_agent_pool' in crawl_config:
                self.config.crawl_user_agent_pool = crawl_config['user_agent_pool']

        # Database configuration
        if 'db' in config_data:
            db_config = config_data['db']
            if 'engine' in db_config:
                self.config.db_engine = db_config['engine']
            if 'dsn' in db_config:
                self.config.db_dsn = db_config['dsn']

        # Validation configuration
        if 'validation' in config_data:
            validation_config = config_data['validation']
            if 'mx_check' in validation_config:
                self.config.validation_mx_check = validation_config['mx_check']
            if 'smtp_check' in validation_config:
                self.config.validation_smtp_check = validation_config['smtp_check']

        # Export configuration
        if 'export' in config_data:
            export_config = config_data['export']
            if 'format' in export_config:
                self.config.export_format = export_config['format']
            if 'path' in export_config:
                self.config.export_path = export_config['path']

        # GDPR configuration
        if 'gdpr' in config_data:
            gdpr_config = config_data['gdpr']
            if 'require_consent' in gdpr_config:
                self.config.gdpr_require_consent = gdpr_config['require_consent']
            if 'mask_unconsented' in gdpr_config:
                self.config.gdpr_mask_unconsented = gdpr_config['mask_unconsented']
            if 'retention_days' in gdpr_config:
                self.config.gdpr_retention_days = gdpr_config['retention_days']

        # Security configuration
        if 'security' in config_data:
            security_config = config_data['security']
            if 'pii_encrypt_at_rest' in security_config:
                self.config.security_pii_encrypt_at_rest = security_config['pii_encrypt_at_rest']
            if 'audit_log' in security_config:
                self.config.security_audit_log = security_config['audit_log']

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration for production."""
        return {
            'engine': self.config.db_engine,
            'dsn': self.config.db_dsn,
            'pool_size': 20,
            'max_overflow': 30,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'echo': False  # Disable SQL logging in production
        }

    def get_crawl_config(self) -> Dict[str, Any]:
        """Get crawling configuration for production."""
        return {
            'workers': self.config.crawl_workers,
            'sources': self.config.crawl_sources,
            'retry_backoff_s': self.config.crawl_retry_backoff_s,
            'max_retries': self.config.crawl_max_retries,
            'user_agent_pool': self.config.crawl_user_agent_pool,
            'rate_limit': 1.0,  # More conservative in production
            'respect_robots_txt': True,
            'concurrent_requests': self.config.crawl_workers
        }

    def get_gdpr_config(self) -> Dict[str, Any]:
        """Get GDPR compliance configuration."""
        return {
            'require_consent': self.config.gdpr_require_consent,
            'mask_unconsented': self.config.gdpr_mask_unconsented,
            'retention_days': self.config.gdpr_retention_days,
            'data_subject_rights': {
                'access': True,
                'rectification': True,
                'erasure': True,
                'portability': True,
                'restriction': True,
                'objection': True
            },
            'lawful_basis': 'legitimate_interest',
            'privacy_policy_url': 'https://yourcompany.com/privacy',
            'contact_dpo': 'dpo@yourcompany.com'
        }

    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration for production."""
        return {
            'pii_encrypt_at_rest': self.config.security_pii_encrypt_at_rest,
            'audit_log': self.config.security_audit_log,
            'encryption_algorithm': 'AES-256-GCM',
            'key_rotation_days': 90,
            'access_logging': True,
            'failed_login_threshold': 5,
            'session_timeout_minutes': 30,
            'require_https': True,
            'secure_headers': True,
            'csrf_protection': True
        }

    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation configuration for production."""
        return {
            'mx_check': self.config.validation_mx_check,
            'smtp_check': self.config.validation_smtp_check,
            'domain_validation': True,
            'syntax_validation': True,
            'disposable_email_check': True,
            'role_account_detection': True,
            'confidence_threshold': 0.8,
            'batch_validation': True,
            'validation_timeout_s': 10
        }

    def get_export_config(self) -> Dict[str, Any]:
        """Get export configuration for production."""
        return {
            'format': self.config.export_format,
            'path': self.config.export_path,
            'compression': 'gzip',
            'encryption': self.config.security_pii_encrypt_at_rest,
            'batch_size': 1000,
            'include_metadata': True,
            'timestamp_format': 'ISO8601',
            'field_mapping': {
                'email': 'email_address',
                'name': 'contact_name',
                'company': 'company_name',
                'title': 'job_title',
                'confidence': 'confidence_score'
            }
        }

    def is_production_mode(self) -> bool:
        """Check if running in production mode."""
        return self.config.profile == "prod"

    def get_full_config(self) -> Dict[str, Any]:
        """Get complete production configuration."""
        return {
            'profile': self.config.profile,
            'database': self.get_database_config(),
            'crawl': self.get_crawl_config(),
            'gdpr': self.get_gdpr_config(),
            'security': self.get_security_config(),
            'validation': self.get_validation_config(),
            'export': self.get_export_config()
        }

    def validate_config(self) -> bool:
        """Validate production configuration."""
        errors = []

        # Validate database configuration
        if not self.config.db_dsn:
            errors.append("Database DSN is required for production")

        if self.config.db_engine not in ['postgres', 'postgresql']:
            errors.append("PostgreSQL is required for production")

        # Validate GDPR compliance
        if not self.config.gdpr_require_consent:
            logger.warning("GDPR consent not required - ensure legal compliance")

        if self.config.gdpr_retention_days < 30:
            errors.append("GDPR retention period should be at least 30 days")

        # Validate security settings
        if not self.config.security_pii_encrypt_at_rest:
            errors.append("PII encryption at rest is required for production")

        if not self.config.security_audit_log:
            errors.append("Audit logging is required for production")

        # Validate crawling configuration
        if self.config.crawl_workers > 16:
            logger.warning("High number of crawl workers may impact performance")

        if errors:
            for error in errors:
                logger.error(f"Configuration validation error: {error}")
            return False

        logger.info("Production configuration validation passed")
        return True

# Global production config instance
