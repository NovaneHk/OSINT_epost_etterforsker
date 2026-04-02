"""
Backend Configuration Module
Simple settings management for FastAPI application
"""

import os
import secrets
from typing import List, Optional
from functools import lru_cache


class Settings:
    """Application settings with environment variable support"""

    # Basic App Settings
    PROJECT_NAME: str = "OSINT E-post Etterforsker API"
    PROJECT_DESCRIPTION: str = "Advanced OSINT B2B Email List Generation System API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SESSION_MAX_AGE: int = 86400  # 24 hours

    # JWT Configuration
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ]
    ALLOWED_HOSTS: List[str] = ["*"]

    # Database Settings
    DATABASE_URL: str = "sqlite:///./data/osint_cache.db"
    CREATE_TABLES_ON_STARTUP: bool = True

    # OSINT Settings
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    MAX_CONCURRENT_CRAWLERS: int = 10
    DEFAULT_CRAWL_DELAY: float = 1.0

    # File Storage
    STATIC_FILES_DIR: Optional[str] = None
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # External APIs
    CLEARBIT_API_KEY: Optional[str] = None
    HUNTER_API_KEY: Optional[str] = None
    HIBP_API_KEY: Optional[str] = None
    SPIDERFOOT_URL: Optional[str] = None
    SPIDERFOOT_API_KEY: Optional[str] = None
    INTELOWL_URL: Optional[str] = "http://localhost:80"
    INTELOWL_API_KEY: Optional[str] = None
    RECONNG_PATH: Optional[str] = None  # Optional explicit path; falls back to PATH lookup

    # Redis
    REDIS_URL: Optional[str] = None

    # GDPR
    GDPR_REQUIRE_CONSENT: bool = False

    # n8n
    N8N_WEBHOOK_URL: Optional[str] = None
    N8N_API_KEY: Optional[str] = None

    # Salesforce
    SALESFORCE_INSTANCE_URL: Optional[str] = None
    SALESFORCE_CLIENT_ID: Optional[str] = None
    SALESFORCE_CLIENT_SECRET: Optional[str] = None

    # HubSpot
    HUBSPOT_ACCESS_TOKEN: Optional[str] = None

    # Microsoft 365
    M365_TENANT_ID: Optional[str] = None
    M365_CLIENT_ID: Optional[str] = None
    M365_CLIENT_SECRET: Optional[str] = None

    # Email Settings
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None

    # Feature Flags
    ENABLE_SMTP_VALIDATION: bool = False
    ENABLE_REAL_TIME_UPDATES: bool = True
    ENABLE_METRICS: bool = True
    SEED_DEFAULT_ADMIN: bool = True
    DEFAULT_ADMIN_EMAIL: str = "admin@example.com"
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "Admin1234"
    DEFAULT_ADMIN_FULL_NAME: str = "System Administrator"

    def __init__(self):
        """Initialize settings from environment variables"""
        # Override defaults with environment variables
        self.PROJECT_NAME = os.getenv("PROJECT_NAME", self.PROJECT_NAME)
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", self.JWT_SECRET_KEY)
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", self.JWT_ALGORITHM)
        self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", str(self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)))
        self.JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", str(self.JWT_REFRESH_TOKEN_EXPIRE_DAYS)))
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", self.ENVIRONMENT)
        self.HOST = os.getenv("HOST", self.HOST)
        self.PORT = int(os.getenv("PORT", self.PORT))
        self.SECRET_KEY = os.getenv("SECRET_KEY", self.SECRET_KEY)
        self.DATABASE_URL = os.getenv("DATABASE_URL", self.DATABASE_URL)
        self.ALLOWED_HOSTS = self._parse_csv_env("ALLOWED_HOSTS", self.ALLOWED_HOSTS)
        self.SEED_DEFAULT_ADMIN = os.getenv(
            "SEED_DEFAULT_ADMIN",
            "true" if self.ENVIRONMENT != "production" else "false"
        ).lower() == "true"
        self.DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", self.DEFAULT_ADMIN_EMAIL)
        self.DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", self.DEFAULT_ADMIN_USERNAME)
        self.DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", self.DEFAULT_ADMIN_PASSWORD)
        self.DEFAULT_ADMIN_FULL_NAME = os.getenv("DEFAULT_ADMIN_FULL_NAME", self.DEFAULT_ADMIN_FULL_NAME)

        # External API keys
        self.CLEARBIT_API_KEY = os.getenv("CLEARBIT_API_KEY", self.CLEARBIT_API_KEY)
        self.HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", self.HUNTER_API_KEY)
        self.HIBP_API_KEY = os.getenv("HIBP_API_KEY", self.HIBP_API_KEY)
        self.REDIS_URL = os.getenv("REDIS_URL", self.REDIS_URL)
        self.GDPR_REQUIRE_CONSENT = os.getenv("GDPR_REQUIRE_CONSENT", "false").lower() == "true"
        self.N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", self.N8N_WEBHOOK_URL)
        self.N8N_API_KEY = os.getenv("N8N_API_KEY", self.N8N_API_KEY)
        self.SALESFORCE_INSTANCE_URL = os.getenv("SALESFORCE_INSTANCE_URL", self.SALESFORCE_INSTANCE_URL)
        self.SALESFORCE_CLIENT_ID = os.getenv("SALESFORCE_CLIENT_ID", self.SALESFORCE_CLIENT_ID)
        self.SALESFORCE_CLIENT_SECRET = os.getenv("SALESFORCE_CLIENT_SECRET", self.SALESFORCE_CLIENT_SECRET)
        self.HUBSPOT_ACCESS_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN", self.HUBSPOT_ACCESS_TOKEN)
        self.M365_TENANT_ID = os.getenv("M365_TENANT_ID", self.M365_TENANT_ID)
        self.M365_CLIENT_ID = os.getenv("M365_CLIENT_ID", self.M365_CLIENT_ID)
        self.M365_CLIENT_SECRET = os.getenv("M365_CLIENT_SECRET", self.M365_CLIENT_SECRET)

        if self.SECRET_KEY == "your-secret-key-change-in-production":
            self.SECRET_KEY = self._build_secret("SECRET_KEY")
        if self.JWT_SECRET_KEY == "your-secret-key-change-in-production":
            self.JWT_SECRET_KEY = self._build_secret("JWT_SECRET_KEY")

        # Parse CORS origins
        self.CORS_ORIGINS = self._parse_csv_env("CORS_ORIGINS", self.CORS_ORIGINS)

        # Validate critical settings
        self._validate_settings()

    def _build_secret(self, env_name: str) -> str:
        env_value = os.getenv(env_name)
        if env_value:
            return env_value

        if self.ENVIRONMENT == "production":
            raise ValueError(f"{env_name} must be set in production")

        return secrets.token_urlsafe(48)

    def _parse_csv_env(self, env_name: str, default: List[str]) -> List[str]:
        raw_value = os.getenv(env_name, "")
        if not raw_value:
            return default

        values = [item.strip() for item in raw_value.split(",") if item.strip()]
        return values or default

    def _validate_settings(self):
        """Validate critical settings"""
        if self.ENVIRONMENT == "production":
            if not self.SECRET_KEY:
                raise ValueError("SECRET_KEY must be set in production")
            if not self.JWT_SECRET_KEY:
                raise ValueError("JWT_SECRET_KEY must be set in production")
            if self.ALLOWED_HOSTS == ["*"]:
                raise ValueError("ALLOWED_HOSTS cannot be wildcard in production")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Convenience function for backward compatibility
def get_config() -> Settings:
    """Get configuration settings"""
    return get_settings()