"""
OSINT B2B Email System - Pytest Configuration and Fixtures

This module provides shared fixtures, configurations, and utilities
for the comprehensive test suite.
"""

import os
import sys

# Set test credentials/configuration BEFORE any backend imports so lru_cached settings pick them up
import tempfile as _tempfile
_TEST_DB_PATH = _tempfile.mktemp(suffix=".test.db")
os.environ["ENVIRONMENT"] = "development"
os.environ["DEFAULT_ADMIN_PASSWORD"] = "Admin1234"
os.environ["SEED_DEFAULT_ADMIN"] = "true"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ.setdefault("RATE_LIMIT_REQUESTS_PER_MINUTE", "600")
os.environ["TESTING"] = "true"
import tempfile
import sqlite3
from pathlib import Path
from typing import Dict, Any, Generator
from unittest.mock import Mock, patch

import pytest
import yaml
from faker import Faker

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import ConfigManager
from core.database import DatabaseManager

# Force-patch backend settings in case lru_cache already fired before our env vars.
# This is safe to do here because lifespan/create_tables hasn't run yet.
try:
    from backend.core.config import get_settings as _get_backend_settings
    _bs = _get_backend_settings()
    _bs.DEFAULT_ADMIN_PASSWORD = "Admin1234"
    _bs.SEED_DEFAULT_ADMIN = True
    _bs.DATABASE_URL = f"sqlite:///{_TEST_DB_PATH}"
    # Propagate to db_manager path if already created
    import backend.core.database as _bdb
    _bdb.settings.DEFAULT_ADMIN_PASSWORD = "Admin1234"
    _bdb.settings.SEED_DEFAULT_ADMIN = True
    _bdb.settings.DATABASE_URL = f"sqlite:///{_TEST_DB_PATH}"
    _bdb.db_manager.db_path = _TEST_DB_PATH
except ImportError:
    pass


# Test configuration
TEST_CONFIG = {
    'database': {
        'path': ':memory:',
        'timeout': 30,
        'check_same_thread': False
    },
    'crawling': {
        'rate_limit': 0.1,
        'max_concurrent': 2,
        'timeout': 5,
        'user_agent': 'OSINT-Test-Bot/1.0'
    },
    'validation': {
        'check_mx': False,
        'check_smtp': False,
        'timeout': 1
    },
    'export': {
        'batch_size': 100,
        'max_file_size': 1048576  # 1MB for tests
    }
}


@pytest.fixture(scope="session")
def faker_instance():
    """Provide a Faker instance for generating test data."""
    fake = Faker(['en_US', 'nb_NO'])
    Faker.seed(42)  # Deterministic test data
    return fake


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide path to test data directory."""
    return Path(__file__).parent / "fixtures" / "data"


@pytest.fixture(scope="function")
def temp_dir():
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="function")
def test_config(temp_dir):
    """Provide test configuration with temporary paths."""
    config = TEST_CONFIG.copy()
    config['database']['path'] = str(temp_dir / "test.db")
    config['export']['output_dir'] = str(temp_dir / "exports")
    config['logging'] = {
        'level': 'DEBUG',
        'file': str(temp_dir / "test.log")
    }
    return config


@pytest.fixture(scope="function")
def config_manager(test_config, temp_dir):
    """Provide a ConfigManager instance with test configuration."""
    config_file = temp_dir / "test_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(test_config, f)

    return ConfigManager(str(config_file))


@pytest.fixture(scope="function")
def database_manager(test_config):
    """Provide a DatabaseManager instance with in-memory database."""
    db_manager = DatabaseManager(test_config['database'])
    db_manager.initialize()
    yield db_manager
    db_manager.close()


@pytest.fixture(scope="function")
def sample_emails(faker_instance):
    """Generate sample email data for testing."""
    emails = []
    domains = ['example.com', 'test.org', 'demo.net', 'sample.co']
    roles = ['ceo', 'cto', 'sales', 'marketing', 'hr', 'info']

    for i in range(50):
        domain = faker_instance.random_element(domains)
        role = faker_instance.random_element(roles)

        email = {
            'email': f"{role}@{domain}",
            'first_name': faker_instance.first_name(),
            'last_name': faker_instance.last_name(),
            'company': faker_instance.company(),
            'title': faker_instance.job(),
            'domain': domain,
            'source_url': faker_instance.url(),
            'confidence_score': faker_instance.random_int(60, 100),
            'role_type': role,
            'sector': faker_instance.random_element(['tech', 'finance', 'healthcare', 'retail']),
            'location': faker_instance.city(),
            'found_at': faker_instance.date_time_this_year().isoformat()
        }
        emails.append(email)

    return emails


@pytest.fixture(scope="function")
def sample_companies(faker_instance):
    """Generate sample company data for testing."""
    companies = []
    sectors = ['Technology', 'Finance', 'Healthcare', 'Retail', 'Manufacturing']

    for i in range(20):
        domain = faker_instance.domain_name()
        company = {
            'domain': domain,
            'name': faker_instance.company(),
            'sector': faker_instance.random_element(sectors),
            'size': faker_instance.random_element(['1-10', '11-50', '51-200', '201-1000', '1000+']),
            'location': faker_instance.city(),
            'website': f"https://{domain}",
            'description': faker_instance.text(max_nb_chars=200),
            'technologies': faker_instance.random_elements(['Python', 'JavaScript', 'React', 'AWS', 'Docker'], length=3),
            'social_media': {
                'linkedin': f"https://linkedin.com/company/{faker_instance.slug()}",
                'twitter': f"https://twitter.com/{faker_instance.user_name()}"
            }
        }
        companies.append(company)

    return companies


@pytest.fixture(scope="function")
def mock_web_response():
    """Provide mock web response for testing crawlers."""
    class MockResponse:
        def __init__(self, html_content: str, status_code: int = 200, url: str = "https://example.com"):
            self.text = html_content
            self.content = html_content.encode('utf-8')
            self.status_code = status_code
            self.url = url
            self.headers = {'Content-Type': 'text/html; charset=utf-8'}

        def json(self):
            return {}

    return MockResponse


@pytest.fixture(scope="function")
def sample_html_content():
    """Provide sample HTML content with emails for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Company - Contact Us</title>
    </head>
    <body>
        <div class="contact-info">
            <h1>Contact Information</h1>
            <p>CEO: <a href="mailto:ceo@testcompany.com">John Doe</a></p>
            <p>Sales: sales@testcompany.com</p>
            <p>Support: support@testcompany.com</p>
            <p>General inquiries: info@testcompany.com</p>
        </div>
        <div class="team">
            <h2>Our Team</h2>
            <div class="member">
                <h3>Jane Smith - CTO</h3>
                <p>Email: jane.smith@testcompany.com</p>
            </div>
            <div class="member">
                <h3>Bob Johnson - Marketing Director</h3>
                <p>Contact: b.johnson@testcompany.com</p>
            </div>
        </div>
        <footer>
            <p>© 2024 Test Company. All rights reserved.</p>
            <p>Privacy: privacy@testcompany.com</p>
        </footer>
    </body>
    </html>
    """


@pytest.fixture(scope="function")
def mock_dns_resolver():
    """Mock DNS resolver for MX record testing."""
    class MockMXRecord:
        def __init__(self, exchange: str, preference: int = 10):
            self.exchange = exchange
            self.preference = preference

    class MockResolver:
        def __init__(self):
            self.valid_domains = {
                'gmail.com': [MockMXRecord('gmail-smtp-in.l.google.com')],
                'outlook.com': [MockMXRecord('outlook-com.olc.protection.outlook.com')],
                'testcompany.com': [MockMXRecord('mail.testcompany.com')],
                'example.com': [MockMXRecord('mail.example.com')]
            }

        def resolve(self, domain: str, record_type: str):
            if record_type == 'MX' and domain in self.valid_domains:
                return self.valid_domains[domain]
            raise Exception(f"No MX record found for {domain}")

    return MockResolver()


@pytest.fixture(scope="function")
def mock_smtp_server():
    """Mock SMTP server for email validation testing."""
    class MockSMTPServer:
        def __init__(self):
            self.valid_emails = {
                'ceo@testcompany.com',
                'sales@testcompany.com',
                'info@example.com',
                'valid@gmail.com'
            }

        def connect(self, host: str, port: int = 25):
            return True

        def helo(self, name: str = 'localhost'):
            return (250, 'OK')

        def mail(self, sender: str):
            return (250, 'OK')

        def rcpt(self, recipient: str):
            if recipient in self.valid_emails:
                return (250, 'OK')
            return (550, 'User unknown')

        def quit(self):
            return (221, 'Bye')

    return MockSMTPServer()


@pytest.fixture(scope="function")
def mock_external_apis():
    """Mock external APIs for testing enrichment services."""
    class MockClearbitAPI:
        def get_company(self, domain: str):
            if domain == 'testcompany.com':
                return {
                    'name': 'Test Company Inc.',
                    'domain': domain,
                    'category': {'industry': 'Technology'},
                    'metrics': {'employees': 150},
                    'location': 'San Francisco, CA'
                }
            return None

    class MockHunterAPI:
        def domain_search(self, domain: str):
            if domain == 'testcompany.com':
                return {
                    'emails': [
                        {'value': 'ceo@testcompany.com', 'type': 'personal'},
                        {'value': 'sales@testcompany.com', 'type': 'generic'}
                    ]
                }
            return {'emails': []}

    return {
        'clearbit': MockClearbitAPI(),
        'hunter': MockHunterAPI()
    }


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Automatically setup test environment for all tests."""
    # Set test environment variables
    monkeypatch.setenv('ENVIRONMENT', 'test')
    monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
    monkeypatch.setenv('DISABLE_EXTERNAL_CALLS', 'true')

    # Mock external service calls by default
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post, \
         patch('smtplib.SMTP') as mock_smtp:

        # Configure default mock responses
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "<html><body>Test page</body></html>"
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {}

        yield


# Performance testing utilities
@pytest.fixture(scope="function")
def performance_monitor():
    """Monitor performance metrics during tests."""
    import time
    import psutil
    import threading

    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.peak_memory = 0
            self.monitoring = False
            self.monitor_thread = None

        def start(self):
            self.start_time = time.time()
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_memory)
            self.monitor_thread.start()

        def stop(self):
            self.end_time = time.time()
            self.monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join()

        def _monitor_memory(self):
            process = psutil.Process()
            while self.monitoring:
                memory_mb = process.memory_info().rss / 1024 / 1024
                self.peak_memory = max(self.peak_memory, memory_mb)
                time.sleep(0.1)

        @property
        def duration(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

        def get_metrics(self):
            return {
                'duration_seconds': self.duration,
                'peak_memory_mb': self.peak_memory
            }

    return PerformanceMonitor()


# Test data validation utilities
def validate_email_format(email: str) -> bool:
    """Validate email format for test assertions."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_test_data_integrity(data: Dict[str, Any]) -> bool:
    """Validate test data integrity."""
    required_fields = ['email', 'domain', 'source_url']
    return all(field in data for field in required_fields)


# Pytest hooks for custom behavior
def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Register custom markers
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "external: mark test as requiring external services")
    config.addinivalue_line("markers", "integration: mark test as integration test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Mark slow tests
        if "slow" in item.name or "performance" in item.name:
            item.add_marker(pytest.mark.slow)

        # Mark external tests
        if "external" in item.name or "api" in item.name:
            item.add_marker(pytest.mark.external)

        # Mark integration tests
        if "integration" in item.name or item.fspath.basename.startswith("test_integration"):
            item.add_marker(pytest.mark.integration)


def pytest_runtest_setup(item):
    """Setup for individual test runs."""
    # Skip external tests if environment variable is set
    if item.get_closest_marker("external") and os.getenv("SKIP_EXTERNAL_TESTS"):
        pytest.skip("Skipping external test due to SKIP_EXTERNAL_TESTS environment variable")


# ---------------------------------------------------------------------------
# Backend API fixtures (shared by backend integration tests)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def backend_client():
    """Session-scoped FastAPI TestClient with running lifespan."""
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def backend_auth(backend_client):
    """Session-scoped auth headers for admin@example.com / Admin1234."""
    response = backend_client.post(
        "/api/auth/token",
        json={"username": "admin@example.com", "password": "Admin1234"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# Aliases used by test_api_integration.py
@pytest.fixture(scope="session")
def test_client(backend_client):
    return backend_client


@pytest.fixture(scope="session")
def auth_headers(backend_auth):
    return backend_auth