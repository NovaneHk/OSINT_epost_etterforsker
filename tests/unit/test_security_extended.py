"""
Unit tests for core/security.py.
Covers uncovered lines: 68-88, 177, 232-243, 254-256, 323-357, 444, 500
"""

import hashlib
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest
from cryptography.fernet import Fernet

from core.security import ComplianceManager, SecurityManager


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_manager() -> SecurityManager:
    """Create SecurityManager with a fresh in-memory key (no file I/O)."""
    with patch("core.security.Path") as mock_path_cls:
        # Make the key-file path look like it doesn't exist
        mock_key_file = MagicMock()
        mock_key_file.exists.return_value = False
        mock_path_cls.return_value = mock_key_file
        # But parent.mkdir should succeed
        mock_key_file.parent.mkdir = MagicMock()
        mgr = SecurityManager(config_manager=None)
    return mgr


# ---------------------------------------------------------------------------
# _get_or_create_encryption_key  (lines 68-88)
# ---------------------------------------------------------------------------

class TestGetOrCreateEncryptionKey:
    """Cover key file read/create branches."""

    def test_reads_existing_key_file(self):
        """Cover lines 65-67: reading existing key."""
        key = Fernet.generate_key()
        with patch("core.security.Path") as mock_path_cls:
            mock_file = MagicMock()
            mock_file.exists.return_value = True
            mock_path_cls.return_value = mock_file
            with patch("builtins.open", mock_open(read_data=key)):
                mgr = SecurityManager(config_manager=None)
        assert mgr.encryption_key == key

    def test_read_exception_falls_back_to_new_key(self):
        """Cover lines 68-69: exception when reading key → create new."""
        with patch("core.security.Path") as mock_path_cls:
            mock_file = MagicMock()
            mock_file.exists.return_value = True
            mock_path_cls.return_value = mock_file
            # open() raises on read
            with patch("builtins.open", side_effect=OSError("no read")):
                with patch("core.security.logger") as mock_log:
                    mgr = SecurityManager(config_manager=None)
            assert mock_log.warning.called

    def test_creates_new_key_when_missing(self):
        """Cover lines 72-88: key file absent → generate and save new key."""
        tmp = tempfile.mkdtemp()
        try:
            key_path = Path(tmp) / ".encryption_key"
            # Let real Path work (file does not yet exist)
            with patch("core.security.Path", return_value=key_path):
                mgr = SecurityManager(config_manager=None)
            assert isinstance(mgr.encryption_key, bytes)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_save_key_exception_is_logged(self):
        """Cover lines 85-86: exception while saving key → error logged."""
        with patch("core.security.Path") as mock_path_cls:
            mock_file = MagicMock()
            mock_file.exists.return_value = False
            mock_path_cls.return_value = mock_file
            # mkdir succeeds, open raises on write
            mock_file.parent.mkdir = MagicMock()
            with patch("builtins.open", side_effect=OSError("no write")):
                with patch("core.security.logger") as mock_log:
                    mgr = SecurityManager(config_manager=None)
            assert mock_log.error.called


# ---------------------------------------------------------------------------
# _validate_email  (line 177 – email too long)
# ---------------------------------------------------------------------------

class TestValidateEmailTooLong:
    def test_email_too_long_adds_issue(self):
        """Cover line 177: email longer than 254 chars."""
        mgr = _make_manager()
        local = "a" * 244
        long_email = f"{local}@example.com"  # > 254 chars
        result = mgr._validate_email(long_email)
        assert "Email too long" in result["email_issues"]


# ---------------------------------------------------------------------------
# secure_database_query – param validation (lines 232-243)
# ---------------------------------------------------------------------------

class TestSecureDatabaseQueryParams:
    def test_valid_query_with_safe_params(self):
        """Cover line 243: passes validation → success."""
        mgr = _make_manager()
        # Patch validate_input to always pass so we reach line 243
        with patch.object(mgr, "validate_input", return_value={"is_valid": True, "threats_detected": []}):
            result = mgr.secure_database_query("any query", ("safe_param",))
        assert result["success"] is True

    def test_dangerous_param_is_blocked(self):
        """Cover lines 232-241: dangerous string param → blocked."""
        mgr = _make_manager()
        # First call (query validation) passes; second call (param) fails
        side_effects = [
            {"is_valid": True, "threats_detected": []},
            {"is_valid": False, "threats_detected": ["SQL injection"]},
        ]
        with patch.object(mgr, "validate_input", side_effect=side_effects):
            result = mgr.secure_database_query("any query", ("bad_param",))
        assert result["success"] is False
        assert "threats" in result

    def test_non_string_param_is_skipped(self):
        """Cover line 233: non-string params skip validation."""
        mgr = _make_manager()
        with patch.object(mgr, "validate_input", return_value={"is_valid": True, "threats_detected": []}):
            result = mgr.secure_database_query("any query", (123,))
        assert result["success"] is True

    def test_params_tuple_empty(self):
        """Empty params tuple → loop skipped, returns success."""
        mgr = _make_manager()
        with patch.object(mgr, "validate_input", return_value={"is_valid": True, "threats_detected": []}):
            result = mgr.secure_database_query("any query")
        assert result["success"] is True


# ---------------------------------------------------------------------------
# encrypt_sensitive_data – exception path (lines 254-256)
# ---------------------------------------------------------------------------

class TestEncryptSensitiveDataException:
    def test_exception_is_raised(self):
        """Cover lines 254-256: Fernet raises → error logged and re-raised."""
        mgr = _make_manager()
        with patch.object(mgr.cipher_suite, "encrypt", side_effect=Exception("enc fail")):
            with patch("core.security.logger") as mock_log:
                with pytest.raises(Exception, match="enc fail"):
                    mgr.encrypt_sensitive_data("secret data")
                mock_log.error.assert_called()


# ---------------------------------------------------------------------------
# validate_file_upload  (lines 323-357)
# ---------------------------------------------------------------------------

class TestValidateFileUpload:
    def test_defaults_allowed_extensions(self):
        """Cover lines 323-324: allowed_extensions defaulted."""
        mgr = _make_manager()
        result = mgr.validate_file_upload("/nonexistent/file.txt")
        # Extension is allowed (.txt), but file doesn't exist → stat raises
        assert "Could not read file" in result["issues"][0]

    def test_disallowed_extension(self):
        """Cover lines 335-337: extension not in list → invalid."""
        mgr = _make_manager()
        result = mgr.validate_file_upload("/some/file.exe")
        assert result["is_valid"] is False
        assert any(".exe" in i for i in result["issues"])

    def test_file_stat_exception_caught(self):
        """Cover lines 347-349: stat() raises → issue added."""
        mgr = _make_manager()
        result = mgr.validate_file_upload("/nonexistent/path/data.csv")
        assert result["is_valid"] is False
        assert any("Could not read file" in i for i in result["issues"])

    def test_file_too_large_flagged(self):
        """Cover line 342-344: file exceeds 10MB."""
        mgr = _make_manager()
        tmp = tempfile.mkdtemp()
        try:
            big_file = Path(tmp) / "big.csv"
            # Create a file that reports size > 10MB via a mock
            big_file.touch()
            with patch("core.security.Path") as mock_pcls:
                mock_pobj = MagicMock()
                mock_pobj.suffix = ".csv"
                mock_pobj.stat.return_value.st_size = 11 * 1024 * 1024
                mock_pobj.__str__ = MagicMock(return_value=str(big_file))
                mock_pcls.return_value = mock_pobj
                # validate_input for path traversal check
                with patch.object(mgr, "validate_input", return_value={"is_valid": True, "threats_detected": []}):
                    result = mgr.validate_file_upload(str(big_file))
            assert result["is_valid"] is False
            assert any("too large" in i for i in result["issues"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_path_traversal_in_filename(self):
        """Cover lines 352-355: path traversal in filename."""
        mgr = _make_manager()
        result = mgr.validate_file_upload("../../etc/passwd.txt")
        assert result["is_valid"] is False

    def test_custom_extensions_list(self):
        """Cover line 326-330: custom extensions passed in."""
        mgr = _make_manager()
        result = mgr.validate_file_upload("/no/file.pdf", allowed_extensions=[".pdf"])
        # Extension ok, but file doesn't exist
        assert any("Could not read file" in i for i in result["issues"])


# ---------------------------------------------------------------------------
# get_security_report – missing key file (line 444)
# ---------------------------------------------------------------------------

class TestGetSecurityReportMissingKey:
    def test_missing_key_file_adds_recommendation(self):
        """Cover line 444: key file missing → recommendation appended."""
        mgr = _make_manager()
        with patch("core.security.Path") as mock_pcls:
            mock_key_file = MagicMock()
            mock_key_file.exists.return_value = False
            mock_pcls.return_value = mock_key_file
            report = mgr.get_security_report()
        assert any("missing" in r.lower() for r in report["recommendations"])

    def test_existing_key_file_no_recommendation(self):
        """Key file present → no recommendation."""
        mgr = _make_manager()
        with patch("core.security.Path") as mock_pcls:
            mock_key_file = MagicMock()
            mock_key_file.exists.return_value = True
            mock_pcls.return_value = mock_key_file
            report = mgr.get_security_report()
        assert report["recommendations"] == []


# ---------------------------------------------------------------------------
# ComplianceManager.generate_privacy_report  (line 500)
# ---------------------------------------------------------------------------

class TestComplianceManagerGeneratePrivacyReport:
    def _make_compliance(self) -> ComplianceManager:
        mgr = _make_manager()
        return ComplianceManager(security_manager=mgr)

    def test_generate_privacy_report_returns_dict(self):
        """Cover line 500: generate_privacy_report returns dict."""
        cm = self._make_compliance()
        report = cm.generate_privacy_report()
        assert isinstance(report, dict)

    def test_generate_privacy_report_structure(self):
        cm = self._make_compliance()
        report = cm.generate_privacy_report()
        # Should have at least a timestamp or similar key
        assert len(report) > 0

    def test_log_data_processing(self):
        cm = self._make_compliance()
        log = cm.log_data_processing("email_addresses", "outreach", "legitimate_interest", "user@example.com")
        assert log["data_type"] == "email_addresses"
        assert log["retention_period"] == 90

    def test_get_retention_period_default(self):
        """Cover default branch in _get_retention_period."""
        cm = self._make_compliance()
        period = cm._get_retention_period("unknown_type")
        assert period == 90

    def test_check_consent_returns_structure(self):
        cm = self._make_compliance()
        result = cm.check_consent("user@example.com", "marketing")
        assert "has_consent" in result
        assert result["has_consent"] is False


# ---------------------------------------------------------------------------
# Additional uncovered methods coverage
# ---------------------------------------------------------------------------

class TestSecurityManagerAdditional:
    def test_sanitize_log_data_strips_newlines(self):
        mgr = _make_manager()
        data = {"msg": "hello\nworld\r\nevil"}
        result = mgr.sanitize_log_data(data)
        assert "\n" not in result["msg"]
        assert "\r" not in result["msg"]

    def test_sanitize_log_data_truncates_long_strings(self):
        mgr = _make_manager()
        long_val = "x" * 1500
        result = mgr.sanitize_log_data({"key": long_val})
        assert len(result["key"]) <= 1003  # 1000 + "..."

    def test_sanitize_log_data_non_string_passthrough(self):
        mgr = _make_manager()
        result = mgr.sanitize_log_data({"num": 42, "lst": [1, 2, 3]})
        assert result["num"] == 42
        assert result["lst"] == [1, 2, 3]

    def test_check_data_integrity_match(self):
        mgr = _make_manager()
        data = "hello world"
        import hashlib
        expected = hashlib.sha256(data.encode()).hexdigest()
        assert mgr.check_data_integrity(data, expected) is True

    def test_check_data_integrity_mismatch(self):
        mgr = _make_manager()
        assert mgr.check_data_integrity("hello", "wronghash" * 4) is False

    def test_validate_csrf_token_match(self):
        mgr = _make_manager()
        token = mgr.generate_csrf_token()
        assert mgr.validate_csrf_token(token, token) is True

    def test_validate_csrf_token_mismatch(self):
        mgr = _make_manager()
        assert mgr.validate_csrf_token("abc", "xyz") is False

    def test_secure_headers_contains_required(self):
        mgr = _make_manager()
        headers = mgr.secure_headers()
        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert "Strict-Transport-Security" in headers

    def test_rate_limit_check_returns_allowed(self):
        mgr = _make_manager()
        result = mgr.rate_limit_check("user_123")
        assert result["allowed"] is True
        assert "remaining_requests" in result

    def test_create_audit_log_sensitive_details_encrypted(self):
        mgr = _make_manager()
        entry = mgr.create_audit_log_entry(
            "login", "user", details={"password": "s3cr3t"}
        )
        assert entry["details_encrypted"] is True

    def test_create_audit_log_non_sensitive_not_encrypted(self):
        mgr = _make_manager()
        entry = mgr.create_audit_log_entry(
            "view", "email", details={"count": 5}
        )
        assert entry["details_encrypted"] is False

    def test_encrypt_and_decrypt_roundtrip_str(self):
        mgr = _make_manager()
        original = "top secret data"
        encrypted = mgr.encrypt_sensitive_data(original)
        decrypted = mgr.decrypt_sensitive_data(encrypted)
        assert decrypted == original

    def test_encrypt_and_decrypt_roundtrip_dict(self):
        mgr = _make_manager()
        original = {"key": "value", "count": 42}
        encrypted = mgr.encrypt_sensitive_data(original)
        decrypted = mgr.decrypt_sensitive_data(encrypted)
        assert decrypted == original

    def test_validate_input_email_type(self):
        mgr = _make_manager()
        result = mgr.validate_input("user@example.com", "email")
        assert "email_valid" in result

    def test_validate_input_domain_type(self):
        mgr = _make_manager()
        result = mgr.validate_input("example.com", "domain")
        assert "domain_valid" in result

    def test_validate_input_url_type(self):
        mgr = _make_manager()
        result = mgr.validate_input("https://example.com", "url")
        assert "url_valid" in result

    def test_validate_input_non_http_url(self):
        mgr = _make_manager()
        result = mgr.validate_input("ftp://example.com", "url")
        assert "Non-HTTP(S) scheme detected" in result.get("url_issues", [])

    def test_validate_input_xss_sanitizes(self):
        mgr = _make_manager()
        xss = "<script>alert('xss')</script>"
        result = mgr.validate_input(xss)
        assert len(result["threats_detected"]) > 0
        assert "&lt;" in result["sanitized_input"]

    def test_validate_input_path_traversal(self):
        mgr = _make_manager()
        result = mgr.validate_input("../../etc/passwd")
        assert result["is_valid"] is False

    def test_validate_input_empty_string(self):
        mgr = _make_manager()
        result = mgr.validate_input("")
        assert result["is_valid"] is True

    def test_hash_and_verify_password(self):
        mgr = _make_manager()
        pwd = "MySecurePassword123!"
        hashed = mgr.hash_password(pwd)
        assert mgr.verify_password(pwd, hashed) is True
        assert mgr.verify_password("wrong", hashed) is False

    def test_verify_password_bad_hash_returns_false(self):
        mgr = _make_manager()
        result = mgr.verify_password("password", "not_a_valid_bcrypt_hash")
        assert result is False

    def test_generate_api_key_length(self):
        mgr = _make_manager()
        key = mgr.generate_api_key(32)
        assert isinstance(key, str)
        assert len(key) > 0

    def test_generate_session_token(self):
        mgr = _make_manager()
        token = mgr.generate_session_token()
        assert isinstance(token, str)
        assert len(token) > 0


# ---------------------------------------------------------------------------
# Additional edge cases for remaining uncovered lines
# ---------------------------------------------------------------------------

class TestSecurityEdgeCases:
    """Cover the remaining uncovered lines."""

    def test_validate_input_sql_injection_sets_invalid(self):
        """Cover lines 106-108, 140: SQL injection detection → is_valid False."""
        mgr = _make_manager()
        result = mgr.validate_input("'; DROP TABLE users; --")
        assert result["is_valid"] is False
        assert result["risk_level"] == "critical"
        assert any("SQL" in t for t in result["threats_detected"])

    def test_validate_input_select_keyword_detected(self):
        """Cover line 140: SELECT keyword triggers SQL injection."""
        mgr = _make_manager()
        result = mgr.validate_input("SELECT * FROM passwords")
        assert result["is_valid"] is False

    def test_validate_email_invalid_format(self):
        """Cover lines 172-173: invalid email format appends issue."""
        mgr = _make_manager()
        result = mgr._validate_email("not-an-email")
        assert result["email_valid"] is False
        assert "Invalid email format" in result["email_issues"]

    def test_validate_email_consecutive_dots(self):
        """Cover line 180: consecutive dots flagged."""
        mgr = _make_manager()
        result = mgr._validate_email("user..name@example.com")
        assert "Consecutive dots detected" in result["email_issues"]

    def test_validate_domain_invalid_format(self):
        """Cover lines 192-193: invalid domain format."""
        mgr = _make_manager()
        result = mgr._validate_domain("not a domain!")
        assert result["domain_valid"] is False
        assert "Invalid domain format" in result["domain_issues"]

    def test_validate_domain_too_long(self):
        """Cover line 196: domain longer than 253 chars."""
        mgr = _make_manager()
        long_domain = ("a" * 63 + ".") * 4 + "com"  # > 253 chars
        result = mgr._validate_domain(long_domain)
        assert "Domain too long" in result["domain_issues"]

    def test_secure_database_query_dangerous_query_blocked(self):
        """Cover lines 224-225: dangerous query logs error and returns failure."""
        mgr = _make_manager()
        with patch("core.security.logger") as mock_log:
            result = mgr.secure_database_query("DROP TABLE users")
        assert result["success"] is False
        assert "threats" in result
        mock_log.error.assert_called()

    def test_decrypt_sensitive_data_exception_raised(self):
        """Cover lines 270-272: invalid ciphertext raises and logs error."""
        mgr = _make_manager()
        import base64
        bad_ciphertext = base64.b64encode(b"not_valid_fernet_data").decode()
        with patch("core.security.logger") as mock_log:
            with pytest.raises(Exception):
                mgr.decrypt_sensitive_data(bad_ciphertext)
            mock_log.error.assert_called()

    def test_chmod_exception_silently_ignored(self):
        """Cover lines 82-83: chmod failure on Windows is silently caught."""
        tmp = tempfile.mkdtemp()
        try:
            key_path = Path(tmp) / ".encryption_key"
            # patch chmod to raise so the bare except runs
            original_chmod = Path.chmod
            def failing_chmod(self, mode):
                raise PermissionError("chmod not supported")
            with patch.object(Path, "chmod", failing_chmod):
                # Patch key file path to our tmp dir
                with patch("core.security.Path", return_value=key_path):
                    mgr = SecurityManager(config_manager=None)
            # Should still have created a valid key
            assert isinstance(mgr.encryption_key, bytes)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
