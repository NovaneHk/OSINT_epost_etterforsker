"""
Unit tests for core/production_config.py
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch
import yaml

from core.production_config import ProductionConfig, ProductionConfigManager


# ---------------------------------------------------------------------------
# ProductionConfig dataclass
# ---------------------------------------------------------------------------

class TestProductionConfig:

    def test_default_profile(self):
        config = ProductionConfig()
        assert config.profile == "prod"

    def test_default_db_engine_postgres(self):
        config = ProductionConfig()
        assert config.db_engine == "postgres"

    def test_default_gdpr_require_consent_true(self):
        config = ProductionConfig()
        assert config.gdpr_require_consent is True

    def test_default_security_encrypt(self):
        config = ProductionConfig()
        assert config.security_pii_encrypt_at_rest is True

    def test_post_init_sets_crawl_sources(self):
        config = ProductionConfig()
        assert config.crawl_sources == ["directories", "events"]

    def test_custom_crawl_sources_not_overwritten(self):
        config = ProductionConfig(crawl_sources=["sites"])
        assert config.crawl_sources == ["sites"]


# ---------------------------------------------------------------------------
# ProductionConfigManager
# ---------------------------------------------------------------------------

class TestProductionConfigManager:

    @pytest.fixture
    def manager_no_file(self, tmp_path):
        """Manager pointing to a non-existent config file."""
        return ProductionConfigManager(config_file=str(tmp_path / "nonexistent.yml"))

    @pytest.fixture
    def manager_with_config(self, tmp_path):
        """Manager pointing to a valid YAML config file."""
        config_yaml = {
            "profile": "prod",
            "crawl": {"workers": 12, "sources": ["directories"], "max_retries": 5},
            "db": {"engine": "postgres", "dsn": "postgresql://user:pass@db:5432/osint"},
            "validation": {"mx_check": True, "smtp_check": True},
            "export": {"format": "json", "path": "out/leads.json"},
            "gdpr": {"require_consent": False, "mask_unconsented": False, "retention_days": 730},
            "security": {"pii_encrypt_at_rest": True, "audit_log": True},
        }
        config_file = tmp_path / "config.prod.yml"
        config_file.write_text(yaml.dump(config_yaml), encoding="utf-8")
        return ProductionConfigManager(config_file=str(config_file))

    def test_defaults_loaded_when_no_file(self, manager_no_file):
        assert manager_no_file.config.profile == "prod"

    def test_profile_loaded_from_file(self, manager_with_config):
        assert manager_with_config.config.profile == "prod"

    def test_crawl_workers_loaded(self, manager_with_config):
        assert manager_with_config.config.crawl_workers == 12

    def test_crawl_sources_loaded(self, manager_with_config):
        assert manager_with_config.config.crawl_sources == ["directories"]

    def test_crawl_max_retries_loaded(self, manager_with_config):
        assert manager_with_config.config.crawl_max_retries == 5

    def test_db_dsn_loaded(self, manager_with_config):
        assert "osint" in manager_with_config.config.db_dsn

    def test_validation_smtp_check_loaded(self, manager_with_config):
        assert manager_with_config.config.validation_smtp_check is True

    def test_export_format_loaded(self, manager_with_config):
        assert manager_with_config.config.export_format == "json"

    def test_gdpr_require_consent_loaded(self, manager_with_config):
        assert manager_with_config.config.gdpr_require_consent is False

    def test_gdpr_retention_days_loaded(self, manager_with_config):
        assert manager_with_config.config.gdpr_retention_days == 730

    def test_invalid_yaml_falls_back_to_defaults(self, tmp_path):
        config_file = tmp_path / "bad.yml"
        config_file.write_text("{ invalid yaml: [", encoding="utf-8")
        manager = ProductionConfigManager(config_file=str(config_file))
        assert manager.config.profile == "prod"

    # --- get_database_config ---

    def test_get_database_config_structure(self, manager_no_file):
        db = manager_no_file.get_database_config()
        assert "engine" in db
        assert "dsn" in db
        assert "pool_size" in db
        assert db["echo"] is False

    def test_get_database_config_engine_default(self, manager_no_file):
        assert manager_no_file.get_database_config()["engine"] == "postgres"

    # --- get_crawl_config ---

    def test_get_crawl_config_structure(self, manager_no_file):
        crawl = manager_no_file.get_crawl_config()
        assert "workers" in crawl
        assert "rate_limit" in crawl
        assert crawl["respect_robots_txt"] is True

    def test_get_crawl_config_concurrent_requests_equals_workers(self, manager_no_file):
        crawl = manager_no_file.get_crawl_config()
        assert crawl["concurrent_requests"] == crawl["workers"]

    # --- get_gdpr_config ---

    def test_get_gdpr_config_structure(self, manager_no_file):
        gdpr = manager_no_file.get_gdpr_config()
        assert "require_consent" in gdpr
        assert "data_subject_rights" in gdpr
        assert gdpr["data_subject_rights"]["erasure"] is True

    # --- get_security_config ---

    def test_get_security_config_structure(self, manager_no_file):
        sec = manager_no_file.get_security_config()
        assert "pii_encrypt_at_rest" in sec
        assert "require_https" in sec
        assert sec["require_https"] is True

    # --- get_validation_config ---

    def test_get_validation_config_structure(self, manager_no_file):
        val = manager_no_file.get_validation_config()
        assert "mx_check" in val
        assert "confidence_threshold" in val
        assert val["disposable_email_check"] is True

    # --- get_export_config ---

    def test_get_export_config_structure(self, manager_no_file):
        exp = manager_no_file.get_export_config()
        assert "format" in exp
        assert "field_mapping" in exp
        assert "email" in exp["field_mapping"]

    # --- is_production_mode ---

    def test_is_production_mode_default_true(self, manager_no_file):
        assert manager_no_file.is_production_mode() is True

    def test_is_production_mode_false_for_dev(self, manager_no_file):
        manager_no_file.config.profile = "dev"
        assert manager_no_file.is_production_mode() is False

    # --- get_full_config ---

    def test_get_full_config_has_all_sections(self, manager_no_file):
        full = manager_no_file.get_full_config()
        for section in ["profile", "database", "crawl", "gdpr", "security", "validation", "export"]:
            assert section in full

    # --- validate_config ---

    def test_validate_config_defaults_pass(self, manager_no_file):
        assert manager_no_file.validate_config() is True

    def test_validate_config_missing_dsn_fails(self, manager_no_file):
        manager_no_file.config.db_dsn = ""
        assert manager_no_file.validate_config() is False

    def test_validate_config_wrong_engine_fails(self, manager_no_file):
        manager_no_file.config.db_engine = "sqlite"
        assert manager_no_file.validate_config() is False

    def test_validate_config_short_retention_fails(self, manager_no_file):
        manager_no_file.config.gdpr_retention_days = 10
        assert manager_no_file.validate_config() is False

    def test_validate_config_no_encryption_fails(self, manager_no_file):
        manager_no_file.config.security_pii_encrypt_at_rest = False
        assert manager_no_file.validate_config() is False

    def test_validate_config_no_audit_log_fails(self, manager_no_file):
        manager_no_file.config.security_audit_log = False
        assert manager_no_file.validate_config() is False
