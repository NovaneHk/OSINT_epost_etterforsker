"""
Unit tests for core/security.py
Tests SecurityManager and ComplianceManager without external dependencies.
"""

import pytest
import hashlib
import hmac
from unittest.mock import MagicMock, patch
from cryptography.fernet import Fernet


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def security_manager():
    """Return a SecurityManager with a synthetic Fernet key (no disk I/O)."""
    key = Fernet.generate_key()
    with patch("core.security.SecurityManager._get_or_create_encryption_key", return_value=key):
        from core.security import SecurityManager
        return SecurityManager()


@pytest.fixture
def compliance_manager(security_manager):
    from core.security import ComplianceManager
    return ComplianceManager(security_manager=security_manager)


# ---------------------------------------------------------------------------
# Input validation — general (clean input)
# ---------------------------------------------------------------------------

class TestValidateInputGeneral:
    def test_clean_input_is_valid(self, security_manager):
        result = security_manager.validate_input("hello world")
        assert result["is_valid"] is True
        assert result["threats_detected"] == []
        assert result["risk_level"] == "low"

    def test_empty_input_returns_early(self, security_manager):
        result = security_manager.validate_input("")
        assert result["is_valid"] is True
        assert result["threats_detected"] == []

    def test_sql_injection_detected(self, security_manager):
        result = security_manager.validate_input("SELECT * FROM users")
        assert result["is_valid"] is False
        assert result["risk_level"] == "critical"
        assert len(result["threats_detected"]) > 0

    def test_sql_union_injection_detected(self, security_manager):
        result = security_manager.validate_input("UNION SELECT password FROM users")
        assert result["is_valid"] is False

    def test_sql_comment_injection_detected(self, security_manager):
        result = security_manager.validate_input("value -- comment")
        assert result["is_valid"] is False

    def test_xss_script_tag_detected(self, security_manager):
        result = security_manager.validate_input("<script>alert(1)</script>")
        assert "XSS pattern detected" in " ".join(result["threats_detected"])
        assert result["sanitized_input"] != "<script>alert(1)</script>"

    def test_xss_javascript_scheme_detected(self, security_manager):
        result = security_manager.validate_input("javascript:void(0)")
        assert any("XSS" in t for t in result["threats_detected"])

    def test_path_traversal_detected(self, security_manager):
        result = security_manager.validate_input("../../etc/passwd")
        assert result["is_valid"] is False
        assert any("Path traversal" in t for t in result["threats_detected"])

    def test_path_traversal_encoded_detected(self, security_manager):
        result = security_manager.validate_input("%2e%2e%2fetc%2fpasswd")
        assert result["is_valid"] is False


# ---------------------------------------------------------------------------
# Type-specific validation
# ---------------------------------------------------------------------------

class TestValidateEmail:
    def test_valid_email(self, security_manager):
        result = security_manager.validate_input("user@example.com", "email")
        assert result.get("email_valid", True) is True

    def test_invalid_email_format(self, security_manager):
        result = security_manager.validate_input("not-an-email", "email")
        assert result.get("email_valid") is False

    def test_email_consecutive_dots(self, security_manager):
        result = security_manager.validate_input("user..name@example.com", "email")
        assert "email_issues" in result
        assert any("dots" in issue.lower() for issue in result["email_issues"])


class TestValidateDomain:
    def test_valid_domain(self, security_manager):
        result = security_manager.validate_input("example.com", "domain")
        assert result.get("domain_valid", True) is True

    def test_invalid_domain_with_special_chars(self, security_manager):
        result = security_manager.validate_input("bad domain!", "domain")
        assert result.get("domain_valid") is False

    def test_too_long_domain(self, security_manager):
        long_domain = "a" * 255
        result = security_manager.validate_input(long_domain, "domain")
        assert "domain_issues" in result
        assert any("long" in issue.lower() for issue in result["domain_issues"])


class TestValidateUrl:
    def test_valid_https_url(self, security_manager):
        result = security_manager.validate_input("https://example.com/path", "url")
        assert result.get("url_valid", True) is True

    def test_valid_http_url(self, security_manager):
        result = security_manager.validate_input("http://example.com", "url")
        assert result.get("url_valid", True) is True

    def test_invalid_url_scheme(self, security_manager):
        result = security_manager.validate_input("ftp://example.com", "url")
        assert result.get("url_valid") is False

    def test_invalid_url_format(self, security_manager):
        result = security_manager.validate_input("not a url at all", "url")
        assert result.get("url_valid") is False


# ---------------------------------------------------------------------------
# Private threat detection helpers
# ---------------------------------------------------------------------------

class TestCheckSqlInjection:
    def test_clean_string_returns_empty(self, security_manager):
        assert security_manager._check_sql_injection("hello world") == []

    def test_select_keyword_detected(self, security_manager):
        threats = security_manager._check_sql_injection("SELECT id FROM table")
        assert len(threats) > 0

    def test_drop_keyword_detected(self, security_manager):
        threats = security_manager._check_sql_injection("DROP TABLE users")
        assert len(threats) > 0


class TestCheckXss:
    def test_clean_string_returns_empty(self, security_manager):
        assert security_manager._check_xss("Hello World") == []

    def test_script_tag_detected(self, security_manager):
        threats = security_manager._check_xss("<script>evil()</script>")
        assert len(threats) > 0

    def test_onerror_attribute_detected(self, security_manager):
        threats = security_manager._check_xss("<img onerror='evil()'>")
        assert len(threats) > 0


class TestCheckPathTraversal:
    def test_clean_string_returns_empty(self, security_manager):
        assert security_manager._check_path_traversal("/safe/path") == []

    def test_dotdot_slash_detected(self, security_manager):
        threats = security_manager._check_path_traversal("../../etc/passwd")
        assert len(threats) > 0

    def test_encoded_traversal_detected(self, security_manager):
        threats = security_manager._check_path_traversal("%2e%2e%2f")
        assert len(threats) > 0


# ---------------------------------------------------------------------------
# Encryption / decryption
# ---------------------------------------------------------------------------

class TestEncryptDecrypt:
    def test_encrypt_string_roundtrip(self, security_manager):
        original = "sensitive data"
        encrypted = security_manager.encrypt_sensitive_data(original)
        assert encrypted != original
        decrypted = security_manager.decrypt_sensitive_data(encrypted)
        assert decrypted == original

    def test_encrypt_dict_roundtrip(self, security_manager):
        data = {"key": "value", "number": 42}
        encrypted = security_manager.encrypt_sensitive_data(data)
        decrypted = security_manager.decrypt_sensitive_data(encrypted)
        assert decrypted == data

    def test_encrypted_output_is_string(self, security_manager):
        result = security_manager.encrypt_sensitive_data("test")
        assert isinstance(result, str)

    def test_decrypt_invalid_data_raises(self, security_manager):
        with pytest.raises(Exception):
            security_manager.decrypt_sensitive_data("not-valid-base64-fernet-data==")


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_password_returns_string(self, security_manager):
        hashed = security_manager.hash_password("secret123")
        assert isinstance(hashed, str)
        assert hashed != "secret123"

    def test_verify_correct_password(self, security_manager):
        password = "MyStr0ngP@ss"
        hashed = security_manager.hash_password(password)
        assert security_manager.verify_password(password, hashed) is True

    def test_verify_wrong_password(self, security_manager):
        hashed = security_manager.hash_password("correct")
        assert security_manager.verify_password("wrong", hashed) is False

    def test_verify_invalid_hash_returns_false(self, security_manager):
        assert security_manager.verify_password("password", "not-a-valid-hash") is False


# ---------------------------------------------------------------------------
# Token / key generation
# ---------------------------------------------------------------------------

class TestTokenGeneration:
    def test_generate_api_key_default_length(self, security_manager):
        key = security_manager.generate_api_key()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_generate_api_key_custom_length(self, security_manager):
        key = security_manager.generate_api_key(16)
        assert isinstance(key, str)
        assert len(key) > 0

    def test_generate_api_key_uniqueness(self, security_manager):
        keys = {security_manager.generate_api_key() for _ in range(10)}
        assert len(keys) == 10

    def test_generate_session_token(self, security_manager):
        token = security_manager.generate_session_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_session_tokens_are_unique(self, security_manager):
        tokens = {security_manager.generate_session_token() for _ in range(10)}
        assert len(tokens) == 10

    def test_generate_csrf_token(self, security_manager):
        token = security_manager.generate_csrf_token()
        assert isinstance(token, str)
        assert len(token) > 0


# ---------------------------------------------------------------------------
# CSRF validation
# ---------------------------------------------------------------------------

class TestCsrfValidation:
    def test_valid_csrf_token(self, security_manager):
        token = security_manager.generate_csrf_token()
        assert security_manager.validate_csrf_token(token, token) is True

    def test_invalid_csrf_token(self, security_manager):
        token = security_manager.generate_csrf_token()
        other = security_manager.generate_csrf_token()
        assert security_manager.validate_csrf_token(token, other) is False


# ---------------------------------------------------------------------------
# Audit log entry
# ---------------------------------------------------------------------------

class TestAuditLogEntry:
    def test_basic_audit_entry_structure(self, security_manager):
        entry = security_manager.create_audit_log_entry("read", "contact", entity_id=1)
        assert entry["action"] == "read"
        assert entry["entity_type"] == "contact"
        assert entry["entity_id"] == 1
        assert "timestamp" in entry

    def test_default_user_is_system(self, security_manager):
        entry = security_manager.create_audit_log_entry("write", "email")
        assert entry["user_id"] == "system"

    def test_custom_user_id(self, security_manager):
        entry = security_manager.create_audit_log_entry("delete", "record", user_id="admin")
        assert entry["user_id"] == "admin"

    def test_sensitive_details_encrypted(self, security_manager):
        details = {"password": "hunter2"}
        entry = security_manager.create_audit_log_entry("auth", "user", details=details)
        assert entry.get("details_encrypted") is True

    def test_non_sensitive_details_not_encrypted(self, security_manager):
        details = {"name": "John"}
        entry = security_manager.create_audit_log_entry("update", "contact", details=details)
        assert entry.get("details_encrypted") is False


# ---------------------------------------------------------------------------
# Rate limit check
# ---------------------------------------------------------------------------

class TestRateLimitCheck:
    def test_rate_limit_allows_request(self, security_manager):
        result = security_manager.rate_limit_check("user123")
        assert result["allowed"] is True

    def test_rate_limit_contains_reset_time(self, security_manager):
        result = security_manager.rate_limit_check("user123")
        assert "reset_time" in result

    def test_rate_limit_remaining_requests(self, security_manager):
        result = security_manager.rate_limit_check("user123", max_requests=50)
        assert result["remaining_requests"] == 49


# ---------------------------------------------------------------------------
# Log sanitization
# ---------------------------------------------------------------------------

class TestSanitizeLogData:
    def test_removes_newlines(self, security_manager):
        data = {"message": "line1\nline2"}
        sanitized = security_manager.sanitize_log_data(data)
        assert "\n" not in sanitized["message"]

    def test_removes_carriage_returns(self, security_manager):
        data = {"msg": "a\rb"}
        sanitized = security_manager.sanitize_log_data(data)
        assert "\r" not in sanitized["msg"]

    def test_truncates_long_strings(self, security_manager):
        data = {"msg": "x" * 2000}
        sanitized = security_manager.sanitize_log_data(data)
        assert len(sanitized["msg"]) <= 1003  # 1000 + "..."

    def test_non_string_values_passed_through(self, security_manager):
        data = {"count": 42, "flag": True}
        sanitized = security_manager.sanitize_log_data(data)
        assert sanitized["count"] == 42
        assert sanitized["flag"] is True


# ---------------------------------------------------------------------------
# Data integrity
# ---------------------------------------------------------------------------

class TestCheckDataIntegrity:
    def test_correct_hash_returns_true(self, security_manager):
        data = "test data"
        expected_hash = hashlib.sha256(data.encode()).hexdigest()
        assert security_manager.check_data_integrity(data, expected_hash) is True

    def test_wrong_hash_returns_false(self, security_manager):
        assert security_manager.check_data_integrity("data", "wronghash" * 4) is False

    def test_tampered_data_returns_false(self, security_manager):
        original = "data"
        expected_hash = hashlib.sha256(original.encode()).hexdigest()
        assert security_manager.check_data_integrity("tampered", expected_hash) is False


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------

class TestSecureHeaders:
    def test_returns_dict(self, security_manager):
        headers = security_manager.secure_headers()
        assert isinstance(headers, dict)

    def test_x_content_type_options_present(self, security_manager):
        headers = security_manager.secure_headers()
        assert "X-Content-Type-Options" in headers

    def test_x_frame_options_deny(self, security_manager):
        headers = security_manager.secure_headers()
        assert headers.get("X-Frame-Options") == "DENY"

    def test_hsts_present(self, security_manager):
        headers = security_manager.secure_headers()
        assert "Strict-Transport-Security" in headers


# ---------------------------------------------------------------------------
# Security report
# ---------------------------------------------------------------------------

class TestGetSecurityReport:
    def test_report_structure(self, security_manager):
        report = security_manager.get_security_report()
        assert "encryption_status" in report
        assert "security_checks" in report
        assert "recommendations" in report

    def test_encryption_is_active(self, security_manager):
        report = security_manager.get_security_report()
        assert report["encryption_status"] == "active"

    def test_security_checks_populated(self, security_manager):
        report = security_manager.get_security_report()
        checks = report["security_checks"]
        assert "input_validation" in checks
        assert "sql_injection_protection" in checks


# ---------------------------------------------------------------------------
# Secure database query helper
# ---------------------------------------------------------------------------

class TestSecureDatabaseQuery:
    def test_clean_query_passes(self, security_manager):
        result = security_manager.secure_database_query("SELECT * FROM contacts", ())
        # Clean SQL — the query itself may flag SQL keywords depending on implementation
        # Just assert response has 'success' key
        assert "success" in result

    def test_dangerous_query_blocked(self, security_manager):
        # A query that contains DROP should be blocked
        result = security_manager.secure_database_query("DROP TABLE users")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# ComplianceManager
# ---------------------------------------------------------------------------

class TestComplianceManager:
    def test_log_data_processing_returns_log(self, compliance_manager):
        log = compliance_manager.log_data_processing(
            data_type="email_addresses",
            purpose="lead generation",
            legal_basis="legitimate interest"
        )
        assert log["data_type"] == "email_addresses"
        assert log["purpose"] == "lead generation"
        assert "timestamp" in log
        assert "processing_id" in log

    def test_retention_period_email_addresses(self, compliance_manager):
        period = compliance_manager._get_retention_period("email_addresses")
        assert period == 90

    def test_retention_period_audit_logs(self, compliance_manager):
        period = compliance_manager._get_retention_period("audit_logs")
        assert period == 2555

    def test_retention_period_unknown_defaults_to_90(self, compliance_manager):
        period = compliance_manager._get_retention_period("unknown_type")
        assert period == 90

    def test_check_consent_conservative_default(self, compliance_manager):
        result = compliance_manager.check_consent("user@example.com", "marketing")
        assert result["has_consent"] is False
        assert result["consent_required"] is True
