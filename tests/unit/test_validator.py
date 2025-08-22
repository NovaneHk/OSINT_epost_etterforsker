"""
Unit tests for email validation functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import dns.resolver
import smtplib
import socket

from validate.validator import EmailValidator, ValidationResult, ValidationLevel, MXRecord


class TestMXRecord:
    """Test MXRecord dataclass"""

    def test_mx_record_creation(self):
        """Test creating an MX record"""
        mx_record = MXRecord(
            hostname="mail.example.com",
            priority=10,
            ttl=300
        )

        assert mx_record.hostname == "mail.example.com"
        assert mx_record.priority == 10
        assert mx_record.ttl == 300

    def test_mx_record_defaults(self):
        """Test MX record with default values"""
        mx_record = MXRecord(
            hostname="mail.example.com",
            priority=10
        )

        assert mx_record.hostname == "mail.example.com"
        assert mx_record.priority == 10
        assert mx_record.ttl is None


class TestValidationLevel:
    """Test ValidationLevel enum"""

    def test_validation_level_values(self):
        """Test validation level enumeration values"""
        assert ValidationLevel.BASIC.value == "basic"
        assert ValidationLevel.SYNTAX.value == "syntax"
        assert ValidationLevel.DOMAIN.value == "domain"
        assert ValidationLevel.MX.value == "mx"
        assert ValidationLevel.SMTP.value == "smtp"
        assert ValidationLevel.FULL.value == "full"


class TestValidationResult:
    """Test ValidationResult dataclass"""

    def test_validation_result_creation(self):
        """Test creating a validation result"""
        mx_records = [
            MXRecord(hostname="mail1.example.com", priority=10),
            MXRecord(hostname="mail2.example.com", priority=20)
        ]

        result = ValidationResult(
            email="test@example.com",
            is_valid=True,
            confidence_score=0.95,
            validation_level=ValidationLevel.FULL,
            syntax_valid=True,
            domain_exists=True,
            mx_records=mx_records,
            smtp_valid=True,
            deliverable=True,
            risk_score=0.1,
            validation_time=2.5
        )

        assert result.email == "test@example.com"
        assert result.is_valid is True
        assert result.confidence_score == 0.95
        assert result.validation_level == ValidationLevel.FULL
        assert result.syntax_valid is True
        assert result.domain_exists is True
        assert len(result.mx_records) == 2
        assert result.smtp_valid is True
        assert result.deliverable is True
        assert result.risk_score == 0.1
        assert result.validation_time == 2.5
        assert result.errors == []
        assert result.timestamp is not None

    def test_validation_result_with_errors(self):
        """Test validation result with errors"""
        result = ValidationResult(
            email="invalid@example.com",
            is_valid=False,
            confidence_score=0.0,
            validation_level=ValidationLevel.SYNTAX,
            errors=["Invalid email format", "Domain not found"]
        )

        assert result.email == "invalid@example.com"
        assert result.is_valid is False
        assert result.confidence_score == 0.0
        assert len(result.errors) == 2
        assert "Invalid email format" in result.errors
        assert "Domain not found" in result.errors


class TestEmailValidator:
    """Test EmailValidator class"""

    @pytest.fixture
    def validator(self):
        """Create an EmailValidator instance for testing"""
        return EmailValidator(
            timeout=5,
            smtp_timeout=10,
            max_retries=2,
            cache_ttl=300,
            user_agent="TestValidator/1.0"
        )

    def test_validator_initialization(self, validator):
        """Test validator initialization"""
        assert validator.timeout == 5
        assert validator.smtp_timeout == 10
        assert validator.max_retries == 2
        assert validator.cache_ttl == 300
        assert validator.user_agent == "TestValidator/1.0"
        assert validator.cache == {}

    def test_validator_default_initialization(self):
        """Test validator with default parameters"""
        validator = EmailValidator()
        assert validator.timeout == 10
        assert validator.smtp_timeout == 30
        assert validator.max_retries == 3
        assert validator.cache_ttl == 3600
        assert "Email-Validator" in validator.user_agent

    def test_validate_syntax_valid_emails(self, validator):
        """Test syntax validation for valid emails"""
        valid_emails = [
            "user@domain.com",
            "first.last@subdomain.domain.co.uk",
            "user+tag@domain.com",
            "user123@domain456.com",
            "test_user@test-domain.com",
            "a@b.co"
        ]

        for email in valid_emails:
            result = validator.validate_syntax(email)
            assert result.is_valid is True, f"Email {email} should be valid"
            assert result.syntax_valid is True
            assert result.validation_level == ValidationLevel.SYNTAX
            assert len(result.errors) == 0

    def test_validate_syntax_invalid_emails(self, validator):
        """Test syntax validation for invalid emails"""
        invalid_emails = [
            "",
            "@domain.com",
            "user@",
            "user@@domain.com",
            "user@domain",
            "user@.com",
            "user@domain.",
            "user name@domain.com",
            "user@domain .com",
            "user@domain..com"
        ]

        for email in invalid_emails:
            result = validator.validate_syntax(email)
            assert result.is_valid is False, f"Email {email} should be invalid"
            assert result.syntax_valid is False
            assert len(result.errors) > 0

    def test_validate_domain_valid(self, validator):
        """Test domain validation for valid domains"""
        with patch('dns.resolver.resolve') as mock_resolve:
            # Mock successful DNS resolution
            mock_resolve.return_value = [Mock(to_text=lambda: "1.2.3.4")]

            result = validator.validate_domain("example.com")

            assert result.is_valid is True
            assert result.domain_exists is True
            assert result.validation_level == ValidationLevel.DOMAIN
            assert len(result.errors) == 0

    def test_validate_domain_invalid(self, validator):
        """Test domain validation for invalid domains"""
        with patch('dns.resolver.resolve') as mock_resolve:
            # Mock DNS resolution failure
            mock_resolve.side_effect = dns.resolver.NXDOMAIN()

            result = validator.validate_domain("nonexistent.invalid")

            assert result.is_valid is False
            assert result.domain_exists is False
            assert "Domain does not exist" in result.errors

    def test_validate_mx_records_valid(self, validator):
        """Test MX record validation for valid domain"""
        with patch('dns.resolver.resolve') as mock_resolve:
            # Mock MX record response
            mock_mx1 = Mock()
            mock_mx1.preference = 10
            mock_mx1.exchange.to_text.return_value = "mail1.example.com."
            mock_mx1.ttl = 300

            mock_mx2 = Mock()
            mock_mx2.preference = 20
            mock_mx2.exchange.to_text.return_value = "mail2.example.com."
            mock_mx2.ttl = 300

            mock_resolve.return_value = [mock_mx1, mock_mx2]

            result = validator.validate_mx_records("example.com")

            assert result.is_valid is True
            assert len(result.mx_records) == 2
            assert result.mx_records[0].hostname == "mail1.example.com"
            assert result.mx_records[0].priority == 10
            assert result.mx_records[1].hostname == "mail2.example.com"
            assert result.mx_records[1].priority == 20
            assert result.validation_level == ValidationLevel.MX

    def test_validate_mx_records_no_mx(self, validator):
        """Test MX record validation for domain without MX records"""
        with patch('dns.resolver.resolve') as mock_resolve:
            # Mock no MX records found
            mock_resolve.side_effect = dns.resolver.NoAnswer()

            result = validator.validate_mx_records("no-mx.example.com")

            assert result.is_valid is False
            assert len(result.mx_records) == 0
            assert "No MX records found" in result.errors

    @patch('smtplib.SMTP')
    def test_validate_smtp_valid(self, mock_smtp_class, validator):
        """Test SMTP validation for valid email"""
        # Mock SMTP connection
        mock_smtp = Mock()
        mock_smtp.helo.return_value = (250, "OK")
        mock_smtp.mail.return_value = (250, "OK")
        mock_smtp.rcpt.return_value = (250, "OK")
        mock_smtp_class.return_value = mock_smtp

        # Mock MX record lookup
        with patch.object(validator, 'validate_mx_records') as mock_mx:
            mock_mx_result = Mock()
            mock_mx_result.is_valid = True
            mock_mx_result.mx_records = [MXRecord(hostname="mail.example.com", priority=10)]
            mock_mx.return_value = mock_mx_result

            result = validator.validate_smtp("test@example.com")

            assert result.is_valid is True
            assert result.smtp_valid is True
            assert result.deliverable is True
            assert result.validation_level == ValidationLevel.SMTP

    @patch('smtplib.SMTP')
    def test_validate_smtp_invalid_email(self, mock_smtp_class, validator):
        """Test SMTP validation for invalid email"""
        # Mock SMTP connection with rejection
        mock_smtp = Mock()
        mock_smtp.helo.return_value = (250, "OK")
        mock_smtp.mail.return_value = (250, "OK")
        mock_smtp.rcpt.return_value = (550, "User unknown")
        mock_smtp_class.return_value = mock_smtp

        # Mock MX record lookup
        with patch.object(validator, 'validate_mx_records') as mock_mx:
            mock_mx_result = Mock()
            mock_mx_result.is_valid = True
            mock_mx_result.mx_records = [MXRecord(hostname="mail.example.com", priority=10)]
            mock_mx.return_value = mock_mx_result

            result = validator.validate_smtp("invalid@example.com")

            assert result.is_valid is False
            assert result.smtp_valid is False
            assert result.deliverable is False
            assert "SMTP validation failed" in result.errors

    @patch('smtplib.SMTP')
    def test_validate_smtp_connection_error(self, mock_smtp_class, validator):
        """Test SMTP validation with connection error"""
        # Mock SMTP connection error
        mock_smtp_class.side_effect = socket.error("Connection refused")

        # Mock MX record lookup
        with patch.object(validator, 'validate_mx_records') as mock_mx:
            mock_mx_result = Mock()
            mock_mx_result.is_valid = True
            mock_mx_result.mx_records = [MXRecord(hostname="mail.example.com", priority=10)]
            mock_mx.return_value = mock_mx_result

            result = validator.validate_smtp("test@example.com")

            assert result.is_valid is False
            assert result.smtp_valid is False
            assert "Connection error" in result.errors

    def test_validate_full_valid_email(self, validator):
        """Test full validation for valid email"""
        email = "test@example.com"

        with patch.object(validator, 'validate_syntax') as mock_syntax, \
             patch.object(validator, 'validate_domain') as mock_domain, \
             patch.object(validator, 'validate_mx_records') as mock_mx, \
             patch.object(validator, 'validate_smtp') as mock_smtp:

            # Mock all validation steps as successful
            mock_syntax.return_value = Mock(is_valid=True, syntax_valid=True, errors=[])
            mock_domain.return_value = Mock(is_valid=True, domain_exists=True, errors=[])
            mock_mx.return_value = Mock(is_valid=True, mx_records=[MXRecord("mail.example.com", 10)], errors=[])
            mock_smtp.return_value = Mock(is_valid=True, smtp_valid=True, deliverable=True, errors=[])

            result = validator.validate_full(email)

            assert result.is_valid is True
            assert result.syntax_valid is True
            assert result.domain_exists is True
            assert result.smtp_valid is True
            assert result.deliverable is True
            assert result.validation_level == ValidationLevel.FULL
            assert result.confidence_score > 0.8

    def test_validate_full_invalid_syntax(self, validator):
        """Test full validation with invalid syntax"""
        email = "invalid-email"

        with patch.object(validator, 'validate_syntax') as mock_syntax:
            mock_syntax.return_value = Mock(is_valid=False, syntax_valid=False, errors=["Invalid format"])

            result = validator.validate_full(email)

            assert result.is_valid is False
            assert result.syntax_valid is False
            assert result.validation_level == ValidationLevel.FULL
            assert "Invalid format" in result.errors

    def test_validate_full_invalid_domain(self, validator):
        """Test full validation with invalid domain"""
        email = "test@nonexistent.invalid"

        with patch.object(validator, 'validate_syntax') as mock_syntax, \
             patch.object(validator, 'validate_domain') as mock_domain:

            mock_syntax.return_value = Mock(is_valid=True, syntax_valid=True, errors=[])
            mock_domain.return_value = Mock(is_valid=False, domain_exists=False, errors=["Domain not found"])

            result = validator.validate_full(email)

            assert result.is_valid is False
            assert result.syntax_valid is True
            assert result.domain_exists is False
            assert "Domain not found" in result.errors

    def test_validate_with_cache(self, validator):
        """Test that validation results are cached"""
        email = "test@example.com"

        # First validation
        with patch.object(validator, 'validate_syntax') as mock_syntax:
            mock_result = Mock(is_valid=True, syntax_valid=True, errors=[])
            mock_syntax.return_value = mock_result

            result1 = validator.validate(email, ValidationLevel.SYNTAX)

            # Verify result
            assert result1.is_valid is True
            assert mock_syntax.call_count == 1

        # Second validation should use cache
        with patch.object(validator, 'validate_syntax') as mock_syntax2:
            result2 = validator.validate(email, ValidationLevel.SYNTAX)

            # Should not call validation again
            assert mock_syntax2.call_count == 0
            assert result2.is_valid is True

    def test_validate_levels(self, validator):
        """Test validation at different levels"""
        email = "test@example.com"

        # Test basic validation
        with patch.object(validator, 'validate_syntax') as mock_syntax:
            mock_syntax.return_value = Mock(is_valid=True)
            result = validator.validate(email, ValidationLevel.BASIC)
            assert result.validation_level == ValidationLevel.BASIC

        # Test syntax validation
        with patch.object(validator, 'validate_syntax') as mock_syntax:
            mock_syntax.return_value = Mock(is_valid=True)
            result = validator.validate(email, ValidationLevel.SYNTAX)
            assert result.validation_level == ValidationLevel.SYNTAX

        # Test domain validation
        with patch.object(validator, 'validate_domain') as mock_domain:
            mock_domain.return_value = Mock(is_valid=True)
            result = validator.validate(email, ValidationLevel.DOMAIN)
            assert result.validation_level == ValidationLevel.DOMAIN

    def test_calculate_confidence_score(self, validator):
        """Test confidence score calculation"""
        # High confidence result
        result_high = ValidationResult(
            email="test@example.com",
            syntax_valid=True,
            domain_exists=True,
            smtp_valid=True,
            deliverable=True,
            mx_records=[MXRecord("mail.example.com", 10)],
            risk_score=0.1
        )

        confidence_high = validator._calculate_confidence_score(result_high)
        assert confidence_high > 0.8

        # Low confidence result
        result_low = ValidationResult(
            email="test@suspicious.com",
            syntax_valid=True,
            domain_exists=False,
            smtp_valid=False,
            deliverable=False,
            mx_records=[],
            risk_score=0.8
        )

        confidence_low = validator._calculate_confidence_score(result_low)
        assert confidence_low < 0.5

    def test_calculate_risk_score(self, validator):
        """Test risk score calculation"""
        # Low risk email
        risk_low = validator._calculate_risk_score("contact@company.com")
        assert risk_low < 0.3

        # Medium risk email (free provider)
        risk_medium = validator._calculate_risk_score("user@gmail.com")
        assert 0.3 <= risk_medium <= 0.7

        # High risk email (suspicious pattern)
        risk_high = validator._calculate_risk_score("temp123@10minutemail.com")
        assert risk_high > 0.7

    def test_is_disposable_email(self, validator):
        """Test disposable email detection"""
        # Known disposable domains
        assert validator._is_disposable_email("test@10minutemail.com") is True
        assert validator._is_disposable_email("test@guerrillamail.com") is True
        assert validator._is_disposable_email("test@tempmail.org") is True

        # Legitimate domains
        assert validator._is_disposable_email("test@gmail.com") is False
        assert validator._is_disposable_email("test@company.com") is False
        assert validator._is_disposable_email("test@university.edu") is False

    def test_is_free_provider(self, validator):
        """Test free email provider detection"""
        # Known free providers
        assert validator._is_free_provider("test@gmail.com") is True
        assert validator._is_free_provider("test@yahoo.com") is True
        assert validator._is_free_provider("test@hotmail.com") is True

        # Business domains
        assert validator._is_free_provider("test@company.com") is False
        assert validator._is_free_provider("test@organization.org") is False

    def test_clear_cache(self, validator):
        """Test cache clearing functionality"""
        # Add something to cache
        validator.cache["test@example.com"] = Mock()
        assert len(validator.cache) == 1

        # Clear cache
        validator.clear_cache()
        assert len(validator.cache) == 0

    def test_validate_batch(self, validator):
        """Test batch validation of multiple emails"""
        emails = [
            "valid@example.com",
            "invalid-email",
            "test@nonexistent.invalid"
        ]

        with patch.object(validator, 'validate') as mock_validate:
            # Mock different results for each email
            mock_validate.side_effect = [
                Mock(is_valid=True, email="valid@example.com"),
                Mock(is_valid=False, email="invalid-email"),
                Mock(is_valid=False, email="test@nonexistent.invalid")
            ]

            results = validator.validate_batch(emails, ValidationLevel.SYNTAX)

            assert len(results) == 3
            assert results[0].is_valid is True
            assert results[1].is_valid is False
            assert results[2].is_valid is False
            assert mock_validate.call_count == 3

    def test_validate_with_timeout(self, validator):
        """Test validation with timeout handling"""
        email = "test@slow-server.com"

        with patch.object(validator, 'validate_smtp') as mock_smtp:
            # Mock timeout exception
            mock_smtp.side_effect = socket.timeout("Timeout")

            result = validator.validate(email, ValidationLevel.SMTP)

            assert result.is_valid is False
            assert "timeout" in str(result.errors).lower()

    def test_validate_with_retries(self, validator):
        """Test validation with retry mechanism"""
        email = "test@unreliable.com"

        with patch('dns.resolver.resolve') as mock_resolve:
            # First call fails, second succeeds
            mock_resolve.side_effect = [
                socket.error("Network error"),
                [Mock(to_text=lambda: "1.2.3.4")]
            ]

            result = validator.validate_domain("unreliable.com")

            # Should succeed on retry
            assert result.is_valid is True
            assert mock_resolve.call_count == 2