"""
Enhanced Test Fixtures for Phase 1 Testing
Comprehensive fixtures for testing all system components
"""

import pytest
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import yaml
from faker import Faker

from core.config import ConfigManager
from core.database import DatabaseManager
from monitoring.health import HealthChecker

fake = Faker()

@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)

@pytest.fixture(scope="session")
def test_config_manager(temp_dir):
    """Create a test configuration manager with test data."""
    config_dir = temp_dir / "configs"
    config_dir.mkdir(exist_ok=True)

    # Create test personas config
    personas_config = {
        'personas': {
            'test_leaders': {
                'description': 'Test technical leaders',
                'roles': ['CTO', 'Tech Lead'],
                'email_patterns': ['cto@', 'tech@'],
                'negative_signals': ['intern', 'junior'],
                'scoring_weight': 40,
                'priority_level': 'high'
            }
        }
    }

    with open(config_dir / "personas.yml", 'w') as f:
        yaml.dump(personas_config, f)

    # Create test sources config
    sources_config = {
        'sources': {
            'test_directories': {
                'type': 'directory',
                'urls': ['https://test-directory.com'],
                'rate_limit': 1.0,
                'enabled': True
            }
        }
    }

    with open(config_dir / "sources.yml", 'w') as f:
        yaml.dump(sources_config, f)

    # Create test rules config
    rules_config = {
        'resource_thresholds': {
            'cpu_warning': 70,
            'cpu_critical': 90,
            'memory_warning': 80,
            'memory_critical': 95,
            'disk_warning': 85,
            'disk_critical': 95
        },
        'email_validation': {
            'min_confidence': 0.6,
            'mx_check': True,
            'smtp_probe': False
        },
        'scoring': {
            'min_score': 70,
            'weights': {
                'persona_match': 0.35,
                'sector_relevance': 0.25,
                'geographic_preference': 0.20,
                'source_credibility': 0.15,
                'data_freshness': 0.05
            }
        }
    }

    with open(config_dir / "rules.yml", 'w') as f:
        yaml.dump(rules_config, f)

    # Create config manager with test directory
    config_manager = ConfigManager()
    config_manager.config_dir = config_dir

    return config_manager

@pytest.fixture(scope="function")
def test_database(temp_dir):
    """Create a test database with sample data."""
    db_path = temp_dir / "test_osint.db"

    # Create database and tables
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()

        # Create companies table
        cursor.execute('''
            CREATE TABLE companies (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                domain TEXT,
                sector TEXT,
                location TEXT,
                retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_url TEXT,
                confidence_score REAL DEFAULT 0.0
            )
        ''')

        # Create emails table
        cursor.execute('''
            CREATE TABLE emails (
                id INTEGER PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                company_id INTEGER,
                role TEXT,
                confidence_score REAL DEFAULT 0.0,
                validation_status TEXT DEFAULT 'pending',
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies (id)
            )
        ''')

        # Create audit_log table
        cursor.execute('''
            CREATE TABLE audit_log (
                id INTEGER PRIMARY KEY,
                action TEXT NOT NULL,
                entity_type TEXT,
                entity_id INTEGER,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT
            )
        ''')

        # Create cache table
        cursor.execute('''
            CREATE TABLE cache (
                id INTEGER PRIMARY KEY,
                key TEXT NOT NULL UNIQUE,
                value TEXT,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create seeds table
        cursor.execute('''
            CREATE TABLE seeds (
                id INTEGER PRIMARY KEY,
                query TEXT NOT NULL,
                persona TEXT,
                sector TEXT,
                geography TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')

        # Insert sample data
        companies_data = [
            ('TechCorp AS', 'techcorp.no', 'technology', 'Oslo', datetime.now() - timedelta(hours=2), 'https://test-source.com', 0.85),
            ('InnovateNow', 'innovatenow.com', 'technology', 'Bergen', datetime.now() - timedelta(hours=1), 'https://test-source.com', 0.92),
            ('DataSolutions', 'datasolutions.se', 'technology', 'Stockholm', datetime.now() - timedelta(minutes=30), 'https://test-source.com', 0.78)
        ]

        cursor.executemany('''
            INSERT INTO companies (name, domain, sector, location, retrieved_at, source_url, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', companies_data)

        # Insert sample emails
        emails_data = [
            ('cto@techcorp.no', 1, 'CTO', 0.95, 'valid'),
            ('tech@innovatenow.com', 2, 'Tech Lead', 0.88, 'valid'),
            ('info@datasolutions.se', 3, 'General', 0.45, 'pending')
        ]

        cursor.executemany('''
            INSERT INTO emails (email, company_id, role, confidence_score, validation_status)
            VALUES (?, ?, ?, ?, ?)
        ''', emails_data)

        # Insert sample seeds
        seeds_data = [
            ('technical_leaders AND technology AND nordics', 'technical_leaders', 'technology', 'nordics', datetime.now() - timedelta(hours=3), 'completed'),
            ('CTO site:linkedin.com technology norway', 'technical_leaders', 'technology', 'nordics', datetime.now() - timedelta(hours=2), 'completed')
        ]

        cursor.executemany('''
            INSERT INTO seeds (query, persona, sector, geography, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', seeds_data)

        conn.commit()

    return str(db_path)

@pytest.fixture
def mock_health_checker(test_config_manager, test_database):
    """Create a mock health checker with test data."""
    health_checker = HealthChecker(test_config_manager)

    # Mock the database path to use test database
    with patch('monitoring.health.Path') as mock_path:
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.stat.return_value.st_size = 1024 * 1024  # 1MB

        yield health_checker

@pytest.fixture
def sample_company_data():
    """Generate sample company data for testing."""
    return {
        'name': fake.company(),
        'domain': fake.domain_name(),
        'sector': fake.random_element(['technology', 'finance', 'healthcare']),
        'location': fake.city(),
        'confidence_score': fake.random.uniform(0.5, 1.0)
    }

@pytest.fixture
def sample_email_data():
    """Generate sample email data for testing."""
    return {
        'email': fake.email(),
        'role': fake.random_element(['CTO', 'Tech Lead', 'VP Engineering']),
        'confidence_score': fake.random.uniform(0.6, 1.0),
        'validation_status': fake.random_element(['valid', 'invalid', 'pending'])
    }

@pytest.fixture
def mock_external_apis():
    """Mock external API responses for testing."""
    with patch('requests.get') as mock_get:
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'success',
            'data': {'test': 'data'}
        }
        mock_get.return_value = mock_response

        yield mock_get

@pytest.fixture
def performance_test_data():
    """Generate large dataset for performance testing."""
    companies = []
    emails = []

    for i in range(1000):
        company = {
            'id': i + 1,
            'name': f"Company_{i}",
            'domain': f"company{i}.com",
            'sector': fake.random_element(['technology', 'finance', 'healthcare']),
            'location': fake.city(),
            'confidence_score': fake.random.uniform(0.5, 1.0)
        }
        companies.append(company)

        # Generate 1-3 emails per company
        for j in range(fake.random.randint(1, 3)):
            email = {
                'email': f"contact{j}@company{i}.com",
                'company_id': i + 1,
                'role': fake.random_element(['CTO', 'Tech Lead', 'Manager']),
                'confidence_score': fake.random.uniform(0.6, 1.0)
            }
            emails.append(email)

    return {'companies': companies, 'emails': emails}

@pytest.fixture
def security_test_inputs():
    """Generate security test inputs for vulnerability testing."""
    return {
        'sql_injection': [
            "'; DROP TABLE companies; --",
            "1' OR '1'='1",
            "admin'/*",
            "1; DELETE FROM emails; --"
        ],
        'xss_payloads': [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert(String.fromCharCode(88,83,83))//'"
        ],
        'path_traversal': [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
    }

@pytest.fixture
def compliance_test_data():
    """Generate test data for GDPR compliance testing."""
    return {
        'personal_data': {
            'emails': ['john.doe@example.com', 'jane.smith@company.com'],
            'names': ['John Doe', 'Jane Smith'],
            'phone_numbers': ['+47 123 45 678', '+46 987 65 432']
        },
        'consent_records': [
            {
                'email': 'john.doe@example.com',
                'consent_given': True,
                'consent_date': datetime.now() - timedelta(days=30),
                'purpose': 'marketing'
            }
        ],
        'data_retention': {
            'retention_period_days': 90,
            'deletion_requests': [
                {
                    'email': 'delete.me@example.com',
                    'request_date': datetime.now() - timedelta(days=7),
                    'status': 'pending'
                }
            ]
        }
    }

@pytest.fixture(autouse=True)
def setup_test_environment(temp_dir, monkeypatch):
    """Set up test environment variables and paths."""
    # Set test environment variables
    monkeypatch.setenv('OSINT_TEST_MODE', 'true')
    monkeypatch.setenv('DATABASE_PATH', str(temp_dir / 'test_osint.db'))
    monkeypatch.setenv('LOG_LEVEL', 'DEBUG')

    # Create test directories
    (temp_dir / 'data').mkdir(exist_ok=True)
    (temp_dir / 'out').mkdir(exist_ok=True)
    (temp_dir / 'logs').mkdir(exist_ok=True)

    yield

    # Cleanup is handled by temp_dir fixture

@pytest.fixture
def benchmark_config():
    """Configuration for performance benchmarking."""
    return {
        'iterations': 100,
        'timeout': 30,
        'memory_limit_mb': 512,
        'cpu_limit_percent': 80,
        'acceptable_response_time_ms': 2000
    }
