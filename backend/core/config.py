"""
Backend Configuration Module
Simple settings management for FastAPI application
"""

import os
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

        # Parse CORS origins
        cors_origins_str = os.getenv("CORS_ORIGINS", "")
        if cors_origins_str:
            self.CORS_ORIGINS = [origin.strip() for origin in cors_origins_str.split(",")]

        # Validate critical settings
        self._validate_settings()

    def _validate_settings(self):
        """Validate critical settings"""
        if self.ENVIRONMENT == "production" and self.SECRET_KEY == "your-secret-key-change-in-production":
            raise ValueError("SECRET_KEY must be set in production")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Convenience function for backward compatibility
def get_config() -> Settings:
    """Get configuration settings"""
    return get_settings()