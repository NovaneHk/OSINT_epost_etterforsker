"""Extended tests for validate/validator.py - covers remaining uncovered lines.

Targets (line numbers):
  125     validate_domain: second retry succeeds but domain not in valid_domains (dead code, skip)
  133-136 validate_domain: unreliable.com second retry also fails
  157     validate_domain: resolve succeeds, domain not in valid_domains
  165-168 validate_domain: outer except (import dns.resolver fails)
  214-215 validate_smtp: "invalid" in email path (rcpt skipped)
  245     validate_smtp: context manager exception
  311-312 validate: except pass in cached-result validation_level set
  326     validate: else/default level branch
  339-340 validate: except pass in non-cached result validation_level set
  430     validate_all_emails: else ContactStatus.UNVALIDATED
  442     validate_all_emails: progress logger at 100 contacts
  499-501 validate_single_email: smtp_probe enabled path
  602-605 _validate_mx_record: DNSException / Exception in A-record fallback
  616-637 _validate_smtp (private): full method body
  685-686 _assess_risk: new domain risk factor
"""

import sys
import pytest
import dns.resolver
import dns.exception
import smtplib
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_validator(rules_config=None, db_manager=None):
    from validate.validator import EmailValidator
    v = EmailValidator.__new__(EmailValidator)
    v.config_manager = None
    v.rules_config = rules_config or {}
    v.validation_cache = {}
    v.seen_emails = set()
    v.domain_role_combinations = set()
    v.cache = {}
    v.timeout = 10
    v.smtp_timeout = 30
    v.max_retries = 3
    v.cache_ttl = 3600
    v.user_agent = "Test/1.0"
    v.db_manager = db_manager or MagicMock()
    return v


# ---------------------------------------------------------------------------
# validate_domain: uncovered paths
# ---------------------------------------------------------------------------

class TestValidateDomainEdgeCases:
    def setup_method(self):
        self.v = _make_validator()

    def test_unreliable_com_second_retry_also_fails(self):
        """Lines 133-136: unreliable.com first AND second DNS resolve fail."""
        call_count = [0]

        def always_fail(domain, record_type):
            call_count[0] += 1
            raise Exception(f"DNS failure #{call_count[0]}")

        with patch("dns.resolver.resolve", side_effect=always_fail):
            result = self.v.validate_domain("unreliable.com")

        assert result.is_valid is False
        assert any("Domain does not exist" in e for e in result.errors)

    def test_resolve_succeeds_domain_not_in_valid_set(self):
        """Line 157: dns.resolver.resolve succeeds; domain is NOT in the hardcoded
        valid_domains set → errors.append('Domain does not exist')."""
        mock_mx = MagicMock()
        with patch("dns.resolver.resolve", return_value=[mock_mx]):
            result = self.v.validate_domain("unknowndomain.xyz")

        assert result.is_valid is False
        assert any("Domain does not exist" in e for e in result.errors)

    def test_outer_except_when_dns_module_unavailable(self):
        """Lines 165-168: outer except triggers when import dns.resolver raises."""
        bad_modules = dict(sys.modules)
        bad_modules["dns.resolver"] = None  # type: ignore[assignment]

        with patch.dict("sys.modules", bad_modules):
            result = self.v.validate_domain("example.com")

        # Outer except returns invalid result
        assert result.is_valid is False
        assert any("Domain does not exist" in e for e in result.errors)


# ---------------------------------------------------------------------------
# validate_smtp (public): uncovered paths
# ---------------------------------------------------------------------------

class TestValidateSmtpEdgeCases:
    def setup_method(self):
        self.v = _make_validator()

    def test_invalid_in_email_no_rcpt_check(self):
        """Lines 214-215: email contains 'invalid'; SMTP mock has no rcpt attr
        so the code skips the code!=250 branch and hits the 'invalid' check."""
        # spec=[] → mock has no helo/mail/rcpt → hasattr checks fail
        mock_smtp = MagicMock(spec=[])

        with patch("smtplib.SMTP", return_value=mock_smtp):
            result = self.v.validate_smtp("invalid@example.com")

        assert result.is_valid is False
        assert result.smtp_valid is False
        assert any("SMTP" in e for e in result.errors)

    def test_context_manager_exception_path(self):
        """Line 245: Exception with 'context manager' in message → special branch."""
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(side_effect=Exception("not a context manager compatible"))
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with patch("smtplib.SMTP", return_value=mock_smtp):
            result = self.v.validate_smtp("user@example.com")

        assert result.is_valid is False
        assert any("SMTP" in e for e in result.errors)


# ---------------------------------------------------------------------------
# validate: uncovered paths
# ---------------------------------------------------------------------------

class TestValidateMethodEdgeCases:
    def setup_method(self):
        self.v = _make_validator()

    def test_cached_result_readonly_validation_level(self):
        """Lines 311-312: cached result has a validation_level setter that raises."""
        from validate.validator import ValidationLevel, ValidationResult

        class _ReadonlyResult:
            """Simulates a result where setting validation_level raises."""
            is_valid = True
            errors = []

            @property
            def validation_level(self):
                return ValidationLevel.SYNTAX

            @validation_level.setter
            def validation_level(self, value):
                raise AttributeError("read-only attribute")

        cached = _ReadonlyResult()
        key = f"test@example.com:{ValidationLevel.SYNTAX}"
        self.v.cache[key] = cached

        # Should not raise; the except pass handles it
        result = self.v.validate("test@example.com", ValidationLevel.SYNTAX)
        assert result is cached

    def test_validate_unknown_level_uses_syntax(self):
        """Line 326: level not matched by any if/elif → else: validate_syntax."""
        from validate.validator import ValidationLevel
        # ValidationLevel.LOW is not BASIC/SYNTAX/DOMAIN/MX/SMTP/FULL
        result = self.v.validate("user@company.com", ValidationLevel.LOW)
        # Falls back to validate_syntax result
        assert hasattr(result, "is_valid")

    def test_noncached_result_readonly_validation_level(self):
        """Lines 339-340: non-cached result object raises when setting validation_level."""
        from validate.validator import ValidationLevel

        class _ReadonlyResult:
            is_valid = True
            errors = []

            @property
            def validation_level(self):
                return None

            @validation_level.setter
            def validation_level(self, value):
                raise AttributeError("frozen result")

        with patch.object(self.v, "validate_syntax", return_value=_ReadonlyResult()):
            result = self.v.validate("test@example.com", ValidationLevel.SYNTAX)

        assert result.is_valid is True


# ---------------------------------------------------------------------------
# validate_all_emails: uncovered paths
# ---------------------------------------------------------------------------

class TestValidateAllEmailsEdgeCases:
    def setup_method(self):
        from core.database import ContactStatus
        self.ContactStatus = ContactStatus

    def _make_contact(self, email="user@company.com", role="Dev", status=None, score=0.5):
        c = MagicMock()
        c.email = email
        c.role = role
        c.status = status or self.ContactStatus.UNVALIDATED
        c.confidence_score = score
        return c

    def _make_validator_with_contacts(self, contacts):
        mock_db = MagicMock()
        mock_db.get_all_contacts.return_value = contacts
        return _make_validator(db_manager=mock_db)

    def test_risky_status_sets_unvalidated(self):
        """Line 430: status 'risky' hits the else branch → ContactStatus.UNVALIDATED."""
        contact = self._make_contact()
        v = self._make_validator_with_contacts([contact])

        with patch.object(v, "validate_single_email",
                          return_value={"status": "risky", "risk_score": 75}):
            result = v.validate_all_emails(aggressive_dedupe=False)

        assert result["total_processed"] == 1
        # contact.status was set to UNVALIDATED in the else branch
        assert contact.status == self.ContactStatus.UNVALIDATED

    def test_unknown_status_sets_unvalidated(self):
        """Line 430: status 'unknown' also hits else branch → ContactStatus.UNVALIDATED."""
        contact = self._make_contact()
        v = self._make_validator_with_contacts([contact])

        with patch.object(v, "validate_single_email",
                          return_value={"status": "unknown", "risk_score": 0}):
            result = v.validate_all_emails(aggressive_dedupe=False)

        assert result["total_processed"] == 1
        assert contact.status == self.ContactStatus.UNVALIDATED

    def test_progress_logged_at_100_contacts(self):
        """Line 442: logger.info fired when total_processed % 100 == 0."""
        contacts = [self._make_contact(email=f"u{i}@co{i}.com", role="Dev")
                    for i in range(100)]
        v = self._make_validator_with_contacts(contacts)

        with patch.object(v, "validate_single_email",
                          return_value={"status": "valid", "risk_score": 5}), \
             patch("validate.validator.logger") as mock_logger:
            result = v.validate_all_emails(aggressive_dedupe=False)

        assert result["total_processed"] == 100
        # logger.info should have been called (including the "100%" progress line at i=100)
        assert mock_logger.info.called


# ---------------------------------------------------------------------------
# validate_single_email: smtp_probe enabled path
# ---------------------------------------------------------------------------

class TestValidateSingleEmailSmtpProbe:
    def test_smtp_probe_enabled_runs_smtp(self):
        """Lines 499-501: smtp_probe=True and rules enable it → _validate_smtp called."""
        rules = {
            "processing_rules": {
                "validation_thresholds": {
                    "smtp_probe_enabled": True
                }
            }
        }
        v = _make_validator(rules_config=rules)

        with patch.object(v, "_validate_format", return_value={"is_valid": True}), \
             patch.object(v, "_validate_mx_record", return_value={"has_mx": True}), \
             patch.object(v, "_validate_smtp",
                          return_value={"smtp_valid": True}) as mock_smtp, \
             patch.object(v, "_assess_risk",
                          return_value={"total_risk_score": 5, "risk_level": "minimal",
                                        "risk_factors": []}):
            result = v.validate_single_email("user@company.com", smtp_probe=True)

        mock_smtp.assert_called_once_with("user@company.com")
        assert result["deliverable"] is True


# ---------------------------------------------------------------------------
# _validate_mx_record: A-record fallback exception paths
# ---------------------------------------------------------------------------

class TestValidateMxRecordAFallbackExceptions:
    def setup_method(self):
        self.v = _make_validator()

    def test_a_fallback_dns_exception(self):
        """Lines 602-603: A-record lookup raises DNSException."""
        def side_effect(domain, record_type):
            if record_type == "MX":
                raise dns.resolver.NoAnswer()
            # A record lookup
            raise dns.exception.DNSException("DNS general error")

        with patch("dns.resolver.resolve", side_effect=side_effect):
            result = self.v._validate_mx_record("user@example.com")

        assert result["has_mx"] is False
        assert "DNS resolution failed" in result.get("error", "")

    def test_a_fallback_unexpected_exception(self):
        """Lines 604-605: A-record lookup raises an unexpected Exception."""
        def side_effect(domain, record_type):
            if record_type == "MX":
                raise dns.resolver.NoAnswer()
            raise RuntimeError("unexpected A record failure")

        with patch("dns.resolver.resolve", side_effect=side_effect):
            result = self.v._validate_mx_record("user@example.com")

        assert result["has_mx"] is False
        assert "Unexpected error during A record lookup" in result.get("error", "")


# ---------------------------------------------------------------------------
# _validate_smtp (private method): full method body
# ---------------------------------------------------------------------------

class TestValidateSmtpPrivateMethod:
    def setup_method(self):
        self.v = _make_validator()

    def test_success_250_response(self):
        """Lines 616-634: _validate_smtp resolves MX, connects, gets 250 OK."""
        mock_mx = MagicMock()
        mock_mx.exchange = MagicMock()
        mock_mx.exchange.__str__ = lambda _self: "smtp.example.com."

        mock_server = MagicMock()
        mock_server.__enter__ = lambda _self: mock_server
        mock_server.__exit__ = MagicMock(return_value=False)
        mock_server.rcpt.return_value = (250, b"OK")

        with patch("dns.resolver.resolve", return_value=[mock_mx]), \
             patch("smtplib.SMTP", return_value=mock_server):
            result = self.v._validate_smtp("user@example.com")

        assert result["smtp_valid"] is True
        assert result["smtp_code"] == 250

    def test_non_250_response_is_invalid(self):
        """Lines 629-631: rcpt returns 550 → smtp_valid=False."""
        mock_mx = MagicMock()
        mock_mx.exchange = MagicMock()
        mock_mx.exchange.__str__ = lambda _self: "smtp.example.com."

        mock_server = MagicMock()
        mock_server.__enter__ = lambda _self: mock_server
        mock_server.__exit__ = MagicMock(return_value=False)
        mock_server.rcpt.return_value = (550, b"User unknown")

        with patch("dns.resolver.resolve", return_value=[mock_mx]), \
             patch("smtplib.SMTP", return_value=mock_server):
            result = self.v._validate_smtp("user@example.com")

        assert result["smtp_valid"] is False

    def test_exception_returns_invalid(self):
        """Lines 636-638: any exception → smtp_valid=False with error string."""
        with patch("dns.resolver.resolve", side_effect=Exception("DNS failed")):
            result = self.v._validate_smtp("user@example.com")

        assert result["smtp_valid"] is False
        assert "DNS failed" in result["error"]

    def test_smtp_message_decoding(self):
        """Line 632: message.decode() called when message is bytes."""
        mock_mx = MagicMock()
        mock_mx.exchange = MagicMock()
        mock_mx.exchange.__str__ = lambda _self: "smtp.example.com."

        mock_server = MagicMock()
        mock_server.__enter__ = lambda _self: mock_server
        mock_server.__exit__ = MagicMock(return_value=False)
        mock_server.rcpt.return_value = (250, b"2.1.5 OK")

        with patch("dns.resolver.resolve", return_value=[mock_mx]), \
             patch("smtplib.SMTP", return_value=mock_server):
            result = self.v._validate_smtp("user@example.com")

        assert result["smtp_message"] == "2.1.5 OK"

    def test_smtp_message_str_type(self):
        """Line 632 (else branch): message is str, not bytes."""
        mock_mx = MagicMock()
        mock_mx.exchange = MagicMock()
        mock_mx.exchange.__str__ = lambda _self: "smtp.example.com."

        mock_server = MagicMock()
        mock_server.__enter__ = lambda _self: mock_server
        mock_server.__exit__ = MagicMock(return_value=False)
        mock_server.rcpt.return_value = (250, "OK string response")

        with patch("dns.resolver.resolve", return_value=[mock_mx]), \
             patch("smtplib.SMTP", return_value=mock_server):
            result = self.v._validate_smtp("user@example.com")

        assert result["smtp_message"] == "OK string response"


# ---------------------------------------------------------------------------
# _assess_risk: new domain
# ---------------------------------------------------------------------------

class TestAssessRiskNewDomain:
    def setup_method(self):
        self.v = _make_validator()

    def test_suspicious_numbered_domain_flagged(self):
        """Lines 685-686: domain passes _is_new_domain → 'new_domain' risk factor added."""
        # "company12345.com" → _is_new_domain matches r'\d{4,}' in the domain
        result = self.v._assess_risk("user@company12345.com")
        assert "new_domain" in result["risk_factors"]
        # Risk score should include the +20 for new domain
        assert result["total_risk_score"] >= 20

    def test_long_random_domain_flagged(self):
        """Lines 685-686: domain with 20+ lowercase chars → new domain."""
        result = self.v._assess_risk("user@abcdefghijklmnopqrstu.com")
        assert "new_domain" in result["risk_factors"]

    def test_alternating_pattern_domain_flagged(self):
        """Lines 685-686: domain with alternating letter/number pattern → new domain."""
        result = self.v._assess_risk("user@ab1cd2ef3.com")
        assert "new_domain" in result["risk_factors"]
