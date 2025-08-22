"""
Simple User Model - Mock for compatibility
"""

class MockUserRole:
    """Mock user role enum"""
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"

    def __init__(self, value):
        self.value = value


class MockUser:
    """Mock user class for compatibility"""

    def __init__(self, id: str = "1", email: str = "admin@example.com",
                 role: str = "ADMIN", is_active: bool = True):
        self.id = id
        self.email = email
        self.role = MockUserRole(role)
        self.is_active = is_active


# For compatibility
User = MockUser
UserRole = MockUserRole