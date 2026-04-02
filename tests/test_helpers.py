"""Test utilities and helper functions"""
import jwt
from datetime import datetime, timedelta
from typing import Optional

# Test configuration
TEST_SECRET_KEY = "test-secret-key"
TEST_ALGORITHM = "HS256"

def create_test_token(
    data: dict = {"sub": "testuser"},
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a test JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)
    
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, TEST_SECRET_KEY, algorithm=TEST_ALGORITHM)

def create_test_user():
    """Create a test user for authentication"""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "is_active": True,
        "is_admin": False
    }

def create_test_contact():
    """Create a test contact for database operations"""
    return {
        "email": "contact@example.com",
        "domain": "example.com",
        "name": "Test Contact",
        "role": "Developer",
        "company": "Test Company",
        "status": "unvalidated",
        "confidence_score": 0.85,
        "overall_score": 0.75,
        "persona_match": "developer",
        "source": "linkedin",
        "source_url": "https://linkedin.com/test",
        "extracted_at": datetime.utcnow().isoformat(),
        "validated_at": None,
        "sector": "Technology"
    }