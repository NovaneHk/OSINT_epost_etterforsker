"""Extended tests for validate/validator.py — covers previously uncovered methods."""
import gc
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
import dns.resolver


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_validator(rules_config=None, db_manager=None):
    """Create an EmailValidator with minimal dependencies."""
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

    mock_db = db_manager or MagicMock()
    v.db_manager = mock_db
    return v


# ---------------------------------------------------------------------------
# EmailMatch
# ---------------------------------------------------------------------------
class TestEmailMatchClass:
    def test_email_match_creation(self):
        from validate.validator import EmailMatch
        m = EmailMatch(email="a@b.com", role="CTO", confidence=0.9, context="ctx")
        assert m.email == "a@b.com"
        assert m.role == "CTO"
        assert m.confidence == pytest.approx(0.9)

    def test_email_match_defaults(self):
        from validate.validator import EmailMatch
        m = EmailMatch()
        assert m.email == ""
        assert m.confidence == 1.0
        assert m.context == ""
        assert m.source_element == ""
        assert m.company_id is None


# ---------------------------------------------------------------------------
# ValidationResult extra paths
# ---------------------------------------------------------------------------
class TestValidationResultExtended:
    def test_kwargs_set_as_attributes(self):
        from validate.validator import ValidationResult
        vr = ValidationResult(email="x@y.com", custom_field="hello")
        assert vr.custom_field == "hello"


# ---------------------------------------------------------------------------
# _validate_format
# ---------------------------------------------------------------------------
class TestValidateFormat:
    def setup_method(self):
        self.v = _make_validator()

    def test_valid_business_email(self):
        result = self.v._validate_format("john.doe@company.com")
        assert result["is_valid"] is True
        assert result["has_valid_tld"] is True
        assert result["is_role_based"] is False

    def test_invalid_no_at_sign(self):
        result = self.v._validate_format("notanemail")
        assert result["is_valid"] is False

    def test_invalid_no_tld(self):
        result = self.v._validate_format("user@localhost")
        assert result["is_valid"] is False

    def test_role_based_email(self):
        result = self.v._validate_format("info@company.com")
        assert result["is_role_based"] is True

    def test_sales_role_based(self):
        result = self.v._validate_format("sales@acme.org")
        assert result["is_role_based"] is True

    def test_length_validity(self):
        # 254 char limit RFC 5321
        long_email = "a" * 249 + "@b.com"  # 255 chars — over limit
        result = self.v._validate_format(long_email)
        # Length exceeds 254
        assert result["length_valid"] is False

    def test_local_part_length_limit(self):
        long_local = "a" * 65 + "@company.com"
        result = self.v._validate_format(long_local)
        assert result["local_part_valid"] is False

    def test_short_tld_invalid(self):
        result = self.v._validate_format("user@company.c")
        assert result["has_valid_tld"] is False

    def test_numeric_tld_invalid(self):
        result = self.v._validate_format("user@company.123")
        assert result["has_valid_tld"] is False


# ---------------------------------------------------------------------------
# _validate_mx_record
# ---------------------------------------------------------------------------
class TestValidateMxRecord:
    def setup_method(self):
        self.v = _make_validator()

    def test_success(self):
        mock_mx = MagicMock()
        mock_mx.preference = 10
        mock_mx.exchange = MagicMock()
        mock_mx.exchange.__str__ = lambda self: "mail.example.com."

        with patch("dns.resolver.resolve", return_value=[mock_mx]):
            result = self.v._validate_mx_record("user@example.com")

        assert result["has_mx"] is True
        assert result["mx_count"] == 1
        assert result["primary_mx"] == "mail.example.com"

    def test_nxdomain(self):
        with patch("dns.resolver.resolve", side_effect=dns.resolver.NXDOMAIN()):
            result = self.v._validate_mx_record("user@nonexistent.invalid")
        assert result["has_mx"] is False
        assert "not found" in result["error"].lower()

    def test_no_answer_with_a_record_fallback(self):
        mock_a = MagicMock()
        a_answer = [mock_a]

        def side_effect(domain, record_type):
            if record_type == "MX":
                raise dns.resolver.NoAnswer()
            return a_answer

        with patch("dns.resolver.resolve", side_effect=side_effect):
            result = self.v._validate_mx_record("user@example.com")
        assert result.get("has_a_record") is True

    def test_no_answer_and_no_a_record(self):
        def side_effect(domain, record_type):
            raise dns.resolver.NoAnswer()

        with patch("dns.resolver.resolve", side_effect=side_effect):
            result = self.v._validate_mx_record("user@example.com")
        assert result["has_mx"] is False

    def test_timeout(self):
        with patch("dns.resolver.resolve", side_effect=dns.exception.Timeout()):
            result = self.v._validate_mx_record("user@example.com")
        assert result["has_mx"] is False
        assert "timeout" in result["error"].lower()

    def test_dns_exception(self):
        with patch("dns.resolver.resolve", side_effect=dns.exception.DNSException("DNS error")):
            result = self.v._validate_mx_record("user@example.com")
        assert result["has_mx"] is False

    def test_unexpected_exception(self):
        with patch("dns.resolver.resolve", side_effect=RuntimeError("unexpected")):
            result = self.v._validate_mx_record("user@example.com")
        assert result["has_mx"] is False


# ---------------------------------------------------------------------------
# _assess_risk
# ---------------------------------------------------------------------------
class TestAssessRisk:
    def setup_method(self):
        self.v = _make_validator()

    def test_disposable_email(self):
        result = self.v._assess_risk("user@10minutemail.com")
        assert result["total_risk_score"] >= 50
        assert "disposable_email_provider" in result["risk_factors"]

    def test_suspicious_number_pattern(self):
        result = self.v._assess_risk("user12345@company.com")
        assert "suspicious_number_pattern" in result["risk_factors"]

    def test_very_short_local_part(self):
        result = self.v._assess_risk("ab@company.com")
        assert "very_short_local_part" in result["risk_factors"]

    def test_consumer_email(self):
        result = self.v._assess_risk("user@gmail.com")
        assert "consumer_email_provider" in result["risk_factors"]

    def test_catch_all_pattern(self):
        result = self.v._assess_risk("catchall@company.com")
        assert "potential_catch_all" in result["risk_factors"]

    def test_clean_business_email(self):
        result = self.v._assess_risk("john.doe@legitcompany.com")
        # Should have minimal risk factors
        assert result["total_risk_score"] < 50

    def test_score_capped_at_100(self):
        # Combine multiple risk factors
        result = self.v._assess_risk("catchall12345@10minutemail.com")
        assert result["total_risk_score"] <= 100

    def test_risk_level_returned(self):
        result = self.v._assess_risk("user@gmail.com")
        assert result["risk_level"] in ("high", "medium", "low", "minimal")


# ---------------------------------------------------------------------------
# _is_new_domain
# ---------------------------------------------------------------------------
class TestIsNewDomain:
    def setup_method(self):
        self.v = _make_validator()

    def test_number_pattern_is_new(self):
        assert self.v._is_new_domain("company12345.com") is True

    def test_long_random_string_is_new(self):
        assert self.v._is_new_domain("abcdefghijklmnopqrstu.com") is True

    def test_normal_domain_not_new(self):
        assert self.v._is_new_domain("microsoft.com") is False

    def test_alternating_pattern_is_new(self):
        assert self.v._is_new_domain("ab1cd2.com") is True


# ---------------------------------------------------------------------------
# _categorize_risk
# ---------------------------------------------------------------------------
class TestCategorizeRisk:
    def setup_method(self):
        self.v = _make_validator()

    def test_high_risk(self):
        assert self.v._categorize_risk(80) == "high"

    def test_medium_risk(self):
        assert self.v._categorize_risk(50) == "medium"

    def test_low_risk(self):
        assert self.v._categorize_risk(25) == "low"

    def test_minimal_risk(self):
        assert self.v._categorize_risk(10) == "minimal"

    def test_boundary_high(self):
        assert self.v._categorize_risk(70) == "high"

    def test_boundary_medium(self):
        assert self.v._categorize_risk(40) == "medium"

    def test_boundary_low(self):
        assert self.v._categorize_risk(20) == "low"


# ---------------------------------------------------------------------------
# _determine_final_status
# ---------------------------------------------------------------------------
class TestDetermineFinalStatus:
    def setup_method(self):
        self.v = _make_validator()

    def _make_result(self, format_valid=True, mx_valid=True, risk_score=0, smtp_valid=None):
        d = {
            "validation_details": {
                "format": {"is_valid": format_valid},
            },
            "mx_valid": mx_valid,
            "risk_score": risk_score,
        }
        if smtp_valid is not None:
            d["validation_details"]["smtp"] = {"smtp_valid": smtp_valid}
        return d

    def test_valid_email(self):
        result = self._make_result()
        assert self.v._determine_final_status(result) == "valid"

    def test_invalid_format(self):
        result = self._make_result(format_valid=False)
        assert self.v._determine_final_status(result) == "invalid"

    def test_high_risk_is_risky(self):
        result = self._make_result(risk_score=75)
        assert self.v._determine_final_status(result) == "risky"

    def test_no_mx_is_invalid(self):
        result = self._make_result(mx_valid=False)
        assert self.v._determine_final_status(result) == "invalid"

    def test_smtp_invalid(self):
        result = self._make_result(smtp_valid=False)
        assert self.v._determine_final_status(result) == "invalid"


# ---------------------------------------------------------------------------
# _check_duplicate
# ---------------------------------------------------------------------------
class TestCheckDuplicate:
    def setup_method(self):
        self.v = _make_validator()

    def test_first_occurrence_not_duplicate(self):
        assert self.v._check_duplicate("user@company.com", "CTO") is False

    def test_second_occurrence_is_duplicate(self):
        self.v._check_duplicate("user@company.com", "CTO")
        assert self.v._check_duplicate("user@company.com", "CTO") is True

    def test_same_domain_role_is_duplicate(self):
        self.v._check_duplicate("alice@company.com", "CTO")
        # Different email, same domain+role combination
        assert self.v._check_duplicate("bob@company.com", "CTO") is True

    def test_different_domain_not_duplicate(self):
        self.v._check_duplicate("alice@companya.com", "CTO")
        assert self.v._check_duplicate("alice@companyb.com", "CTO") is False

    def test_case_insensitive_email(self):
        self.v._check_duplicate("User@Company.com", "CTO")
        assert self.v._check_duplicate("user@company.com", "CTO") is True


# ---------------------------------------------------------------------------
# validate_single_email
# ---------------------------------------------------------------------------
class TestValidateSingleEmail:
    def setup_method(self):
        self.v = _make_validator(rules_config={})

    def test_invalid_format_returns_early(self):
        result = self.v.validate_single_email("notanemail")
        assert result["status"] == "invalid"
        assert result["risk_score"] == 100

    def test_mx_invalid_returns_invalid(self):
        with patch.object(self.v, "_validate_format", return_value={"is_valid": True}), \
             patch.object(self.v, "_validate_mx_record", return_value={"has_mx": False}):
            result = self.v.validate_single_email("user@nodomain.invalid")
        assert result["status"] == "invalid"
        assert result["risk_score"] == 90

    def test_valid_flow(self):
        with patch.object(self.v, "_validate_format", return_value={"is_valid": True}), \
             patch.object(self.v, "_validate_mx_record", return_value={"has_mx": True}), \
             patch.object(self.v, "_assess_risk", return_value={"total_risk_score": 10, "risk_level": "minimal", "risk_factors": []}):
            result = self.v.validate_single_email("good@company.com")
        assert result["status"] in ("valid", "risky")

    def test_caching_works(self):
        with patch.object(self.v, "_validate_format", return_value={"is_valid": True}), \
             patch.object(self.v, "_validate_mx_record", return_value={"has_mx": True}), \
             patch.object(self.v, "_assess_risk", return_value={"total_risk_score": 5, "risk_level": "minimal", "risk_factors": []}):
            r1 = self.v.validate_single_email("cache@company.com")
            r2 = self.v.validate_single_email("cache@company.com")
        assert r1 is r2

    def test_exception_returns_unknown(self):
        with patch.object(self.v, "_validate_format", side_effect=RuntimeError("boom")):
            result = self.v.validate_single_email("user@company.com")
        assert result["status"] == "unknown"

    def test_smtp_probe_skipped_when_disabled(self):
        """smtp_probe is skipped when rules don't enable it."""
        v = _make_validator(rules_config={"processing_rules": {"validation_thresholds": {"smtp_probe_enabled": False}}})
        with patch.object(v, "_validate_format", return_value={"is_valid": True}), \
             patch.object(v, "_validate_mx_record", return_value={"has_mx": True}), \
             patch.object(v, "_assess_risk", return_value={"total_risk_score": 5, "risk_level": "minimal", "risk_factors": []}), \
             patch.object(v, "_validate_smtp") as mock_smtp:
            v.validate_single_email("user@company.com", smtp_probe=True)
        mock_smtp.assert_not_called()

    def test_no_mx_check_skips_mx(self):
        with patch.object(self.v, "_validate_format", return_value={"is_valid": True}), \
             patch.object(self.v, "_validate_mx_record") as mock_mx, \
             patch.object(self.v, "_assess_risk", return_value={"total_risk_score": 5, "risk_level": "minimal", "risk_factors": []}):
            self.v.validate_single_email("user@company.com", mx_check=False)
        mock_mx.assert_not_called()


# ---------------------------------------------------------------------------
# validate_all_emails
# ---------------------------------------------------------------------------
class TestValidateAllEmails:
    def setup_method(self):
        from core.database import Contact, ContactStatus
        self.Contact = Contact
        self.ContactStatus = ContactStatus

    def _make_validator_with_contacts(self, contacts):
        mock_db = MagicMock()
        mock_db.get_all_contacts.return_value = contacts
        v = _make_validator(db_manager=mock_db)
        return v

    def test_empty_contacts(self):
        v = self._make_validator_with_contacts([])
        result = v.validate_all_emails()
        assert result["total_processed"] == 0
        assert result["validation_rate"] == 0

    def test_valid_contact_processed(self):
        contact = MagicMock()
        contact.email = "user@company.com"
        contact.role = "CTO"
        contact.status = self.ContactStatus.UNVALIDATED
        contact.confidence_score = 0.5

        v = self._make_validator_with_contacts([contact])
        with patch.object(v, "validate_single_email", return_value={"status": "valid", "risk_score": 10}):
            result = v.validate_all_emails()
        assert result["total_processed"] == 1
        assert result["status_breakdown"]["valid"] == 1

    def test_invalid_contact_processed(self):
        contact = MagicMock()
        contact.email = "bad@invalid"
        contact.role = ""
        contact.status = self.ContactStatus.UNVALIDATED
        contact.confidence_score = 0.1

        v = self._make_validator_with_contacts([contact])
        with patch.object(v, "validate_single_email", return_value={"status": "invalid", "risk_score": 100}):
            result = v.validate_all_emails()
        assert result["status_breakdown"]["invalid"] == 1

    def test_duplicate_marked(self):
        contact = MagicMock()
        contact.email = "dup@company.com"
        contact.role = "Sales"
        contact.status = self.ContactStatus.UNVALIDATED
        contact.confidence_score = 0.5

        v = self._make_validator_with_contacts([contact])
        with patch.object(v, "validate_single_email", return_value={"status": "valid", "risk_score": 5}), \
             patch.object(v, "_check_duplicate", return_value=True):
            result = v.validate_all_emails(aggressive_dedupe=True)
        assert result["status_breakdown"].get("duplicate", 0) >= 1

    def test_exception_during_validation_counted(self):
        contact = MagicMock()
        contact.email = "error@company.com"
        contact.role = "Dev"
        contact.status = self.ContactStatus.UNVALIDATED
        contact.confidence_score = 0.5

        v = self._make_validator_with_contacts([contact])
        with patch.object(v, "validate_single_email", side_effect=RuntimeError("boom")):
            result = v.validate_all_emails()
        assert result["total_processed"] == 1
        assert result["status_breakdown"]["unknown"] >= 1

    def test_validation_rate_calculated(self):
        contacts = []
        for i in range(4):
            c = MagicMock()
            c.email = f"user{i}@company{i}.com"  # unique domains → no deduplication
            c.role = "CTO"
            c.status = self.ContactStatus.UNVALIDATED
            c.confidence_score = 0.8
            contacts.append(c)

        v = self._make_validator_with_contacts(contacts)
        statuses = ["valid", "valid", "invalid", "invalid"]
        with patch.object(v, "validate_single_email", side_effect=[
            {"status": s, "risk_score": 5} for s in statuses
        ]):
            result = v.validate_all_emails(aggressive_dedupe=False)
        assert result["validation_rate"] == pytest.approx(50.0, abs=1)


# ---------------------------------------------------------------------------
# get_validation_statistics
# ---------------------------------------------------------------------------
class TestGetValidationStatistics:
    def test_empty_emails(self):
        mock_db = MagicMock()
        mock_db.get_emails.return_value = []
        v = _make_validator(db_manager=mock_db)
        result = v.get_validation_statistics()
        assert result == {"total_emails": 0}

    def test_with_emails(self):
        emails = [
            {"validation_status": "valid", "mx_valid": True, "deliverable": True, "risk_score": 10},
            {"validation_status": "invalid", "mx_valid": False, "deliverable": False, "risk_score": 90},
            {"validation_status": "valid", "mx_valid": True, "deliverable": False, "risk_score": 20},
        ]
        mock_db = MagicMock()
        mock_db.get_emails.return_value = emails
        v = _make_validator(db_manager=mock_db)
        result = v.get_validation_statistics()

        assert result["total_emails"] == 3
        assert result["status_breakdown"]["valid"] == 2
        assert result["status_breakdown"]["invalid"] == 1
        assert result["mx_valid_rate"] == pytest.approx(66.67, abs=0.1)
        assert result["cache_size"] == 0
