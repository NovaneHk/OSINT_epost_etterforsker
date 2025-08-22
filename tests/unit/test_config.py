"""
Unit tests for configuration management
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import yaml

from core.config import ConfigManager, SystemConfig


class TestSystemConfig:
    """Test SystemConfig dataclass"""

    def test_default_values(self):
        config = SystemConfig()
        assert config.default_persona == "technical_leaders"
        assert config.default_sector == "technology"
        assert config.default_geo == "nordics"
        assert config.rate_limit == 2.0
        assert config.max_concurrent == 10
        assert config.data_retention_days == 90
        assert config.gdpr_compliance_mode is True


class TestConfigManager:
    """Test ConfigManager class"""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create ConfigManager with temporary directory"""
        return ConfigManager(config_dir=temp_config_dir)

    def test_init_creates_config_directory(self, temp_config_dir):
        config_path = Path(temp_config_dir)
        assert config_path.exists()

        # Test that ConfigManager creates the directory
        new_dir = config_path / "new_configs"
        ConfigManager(config_dir=str(new_dir))
        assert new_dir.exists()

    def test_ensure_config_files_creates_defaults(self, config_manager, temp_config_dir):
        """Test that default config files are created"""
        config_path = Path(temp_config_dir)

        expected_files = ['personas.yml', 'sources.yml', 'rules.yml']

        for filename in expected_files:
            file_path = config_path / filename
            assert file_path.exists(), f"{filename} should be created"

            # Test that file contains valid YAML
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                assert data is not None, f"{filename} should contain valid YAML"

    def test_load_personas(self, config_manager):
        """Test loading personas configuration"""
        personas = config_manager.load_personas()

        assert 'personas' in personas
        assert isinstance(personas['personas'], dict)

        # Check for expected persona types
        expected_personas = ['technical_leaders', 'procurement_specialists']
        for persona in expected_personas:
            assert persona in personas['personas']

        # Check persona structure
        tech_leaders = personas['personas']['technical_leaders']
        assert 'roles' in tech_leaders
        assert 'email_patterns' in tech_leaders
        assert 'scoring_weight' in tech_leaders
        assert isinstance(tech_leaders['roles'], list)
        assert isinstance(tech_leaders['email_patterns'], list)

    def test_load_sources(self, config_manager):
        """Test loading sources configuration"""
        sources = config_manager.load_sources()

        assert 'source_categories' in sources
        assert isinstance(sources['source_categories'], dict)

        # Check for expected source categories
        expected_categories = ['directories', 'events']
        for category in expected_categories:
            assert category in sources['source_categories']

    def test_load_rules(self, config_manager):
        """Test loading rules configuration"""
        rules = config_manager.load_rules()

        assert 'processing_rules' in rules
        assert isinstance(rules['processing_rules'], dict)

        # Check for expected rule sections
        expected_sections = ['rate_limiting', 'validation_thresholds', 'scoring_weights']
        for section in expected_sections:
            assert section in rules['processing_rules']

    def test_get_current_config(self, config_manager):
        """Test getting current configuration"""
        config = config_manager.get_current_config()

        assert 'system' in config
        assert 'personas' in config
        assert 'sources' in config
        assert 'rules' in config

        # Test system config structure
        system_config = config['system']
        assert 'default_persona' in system_config
        assert 'rate_limit' in system_config

    def test_update_config(self, config_manager):
        """Test updating system configuration"""
        original_rate_limit = config_manager.system_config.rate_limit

        updates = {
            'rate_limit': 3.0,
            'max_concurrent': 15
        }

        config_manager.update_config(updates)

        assert config_manager.system_config.rate_limit == 3.0
        assert config_manager.system_config.max_concurrent == 15

        # Test invalid key is ignored
        config_manager.update_config({'invalid_key': 'value'})
        # Should not raise error, just ignore

    def test_load_yaml_config_file_not_found(self, config_manager, temp_config_dir):
        """Test loading non-existent YAML file"""
        # Remove a config file
        config_path = Path(temp_config_dir) / 'personas.yml'
        config_path.unlink()

        # Should return empty dict
        result = config_manager._load_yaml_config('personas.yml')
        assert result == {}

    def test_load_yaml_config_invalid_yaml(self, config_manager, temp_config_dir):
        """Test loading invalid YAML file"""
        config_path = Path(temp_config_dir) / 'invalid.yml'

        # Write invalid YAML
        with open(config_path, 'w') as f:
            f.write("invalid: yaml: content: [")

        result = config_manager._load_yaml_config('invalid.yml')
        assert result == {}

    def test_default_personas_config_structure(self, config_manager):
        """Test structure of default personas configuration"""
        personas_config = config_manager._default_personas_config()

        assert 'personas' in personas_config
        personas = personas_config['personas']

        # Test technical_leaders persona
        tech = personas['technical_leaders']
        assert 'description' in tech
        assert 'roles' in tech
        assert 'email_patterns' in tech
        assert 'negative_signals' in tech
        assert 'scoring_weight' in tech
        assert 'priority_level' in tech

        # Test data types
        assert isinstance(tech['roles'], list)
        assert isinstance(tech['email_patterns'], list)
        assert isinstance(tech['negative_signals'], list)
        assert isinstance(tech['scoring_weight'], int)
        assert tech['priority_level'] in ['high', 'medium', 'low']

    def test_default_sources_config_structure(self, config_manager):
        """Test structure of default sources configuration"""
        sources_config = config_manager._default_sources_config()

        assert 'source_categories' in sources_config
        categories = sources_config['source_categories']

        # Test directories category
        directories = categories['directories']
        assert 'priority' in directories
        assert 'daily_limit' in directories
        assert 'sources' in directories
        assert isinstance(directories['sources'], list)

        # Test source structure
        if directories['sources']:
            source = directories['sources'][0]
            assert 'name' in source
            assert 'url' in source
            assert 'credibility_score' in source
            assert 'enabled' in source

    def test_default_rules_config_structure(self, config_manager):
        """Test structure of default rules configuration"""
        rules_config = config_manager._default_rules_config()

        assert 'processing_rules' in rules_config
        rules = rules_config['processing_rules']

        # Test rate limiting
        rate_limiting = rules['rate_limiting']
        assert 'requests_per_second' in rate_limiting
        assert 'max_concurrent' in rate_limiting
        assert isinstance(rate_limiting['requests_per_second'], (int, float))

        # Test validation thresholds
        validation = rules['validation_thresholds']
        assert 'min_confidence_score' in validation
        assert 'require_mx_validation' in validation

        # Test scoring weights
        scoring = rules['scoring_weights']
        assert 'persona_match' in scoring
        assert 'sector_relevance' in scoring

        # Test weights sum to approximately 1.0
        total_weight = sum(scoring.values())
        assert abs(total_weight - 1.0) < 0.01