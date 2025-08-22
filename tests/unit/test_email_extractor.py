"""
Unit tests for email extraction functionality
"""

import pytest
from unittest.mock import Mock, patch
import re

from extract.email_extractor import EmailExtractor, EmailMatch, ExtractionResult


class TestEmailMatch:
    """Test EmailMatch dataclass"""

    def test_email_match_creation(self):
        """Test creating an email match"""
        match = EmailMatch(
            email="test@example.com",
            domain="example.com",
            local_part="test",
            context="Contact us at test@example.com for support",
            position=14,
            confidence=0.95,
            match_type="standard"
        )

        assert match.email == "test@example.com"
        assert match.domain == "example.com"
        assert match.local_part == "test"
        assert match.context == "Contact us at test@example.com for support"
        assert match.position == 14
        assert match.confidence == 0.95
        assert match.match_type == "standard"

    def test_email_match_defaults(self):
        """Test email match with default values"""
        match = EmailMatch(
            email="test@example.com",
            domain="example.com",
            local_part="test"
        )

        assert match.email == "test@example.com"
        assert match.domain == "example.com"
        assert match.local_part == "test"
        assert match.context is None
        assert match.position == 0
        assert match.confidence == 1.0
        assert match.match_type == "standard"


class TestExtractionResult:
    """Test ExtractionResult dataclass"""

    def test_extraction_result_creation(self):
        """Test creating an extraction result"""
        email_matches = [
            EmailMatch(email="test1@example.com", domain="example.com", local_part="test1"),
            EmailMatch(email="test2@example.com", domain="example.com", local_part="test2")
        ]

        result = ExtractionResult(
            source_url="https://example.com",
            email_matches=email_matches,
            total_emails=2,
            unique_domains={"example.com"},
            extraction_time=1.5,
            success=True
        )

        assert result.source_url == "https://example.com"
        assert len(result.email_matches) == 2
        assert result.total_emails == 2
        assert result.unique_domains == {"example.com"}
        assert result.extraction_time == 1.5
        assert result.success is True
        assert result.error is None
        assert result.timestamp is not None

    def test_extraction_result_with_error(self):
        """Test extraction result with error"""
        result = ExtractionResult(
            source_url="https://example.com",
            success=False,
            error="Failed to parse content"
        )

        assert result.source_url == "https://example.com"
        assert result.success is False
        assert result.error == "Failed to parse content"
        assert result.email_matches == []
        assert result.total_emails == 0
        assert result.unique_domains == set()


class TestEmailExtractor:
    """Test EmailExtractor class"""

    @pytest.fixture
    def extractor(self):
        """Create an EmailExtractor instance for testing"""
        return EmailExtractor(
            min_confidence=0.8,
            max_context_chars=50,
            exclude_domains=["spam.com", "temporary.com"],
            exclude_patterns=[r"noreply@", r"no-reply@"]
        )

    def test_extractor_initialization(self, extractor):
        """Test extractor initialization"""
        assert extractor.min_confidence == 0.8
        assert extractor.max_context_chars == 50
        assert "spam.com" in extractor.exclude_domains
        assert "temporary.com" in extractor.exclude_domains
        assert len(extractor.exclude_patterns) == 2

        # Test compiled regex patterns
        assert all(isinstance(pattern, re.Pattern) for pattern in extractor.exclude_patterns)

    def test_extractor_default_initialization(self):
        """Test extractor with default parameters"""
        extractor = EmailExtractor()
        assert extractor.min_confidence == 0.5
        assert extractor.max_context_chars == 100
        assert extractor.exclude_domains == set()
        assert extractor.exclude_patterns == []

    def test_basic_email_extraction(self, extractor):
        """Test basic email extraction from text"""
        text = """
        Contact us at support@example.com for help.
        Sales inquiries: sales@example.com
        For urgent matters, reach admin@example.com
        """

        result = extractor.extract_from_text(text, source_url="https://example.com")

        assert result.success is True
        assert result.total_emails == 3
        assert len(result.email_matches) == 3
        assert result.unique_domains == {"example.com"}

        # Check extracted emails
        extracted_emails = [match.email for match in result.email_matches]
        assert "support@example.com" in extracted_emails
        assert "sales@example.com" in extracted_emails
        assert "admin@example.com" in extracted_emails

    def test_email_extraction_with_context(self, extractor):
        """Test email extraction with context capture"""
        text = "For customer support, please contact support@example.com during business hours."

        result = extractor.extract_from_text(text, source_url="https://example.com")

        assert result.success is True
        assert len(result.email_matches) == 1

        match = result.email_matches[0]
        assert match.email == "support@example.com"
        assert "customer support" in match.context
        assert "business hours" in match.context
        assert match.position > 0

    def test_email_extraction_excludes_domains(self, extractor):
        """Test that excluded domains are filtered out"""
        text = """
        Valid email: good@example.com
        Spam email: bad@spam.com
        Temporary: temp@temporary.com
        """

        result = extractor.extract_from_text(text, source_url="https://example.com")

        assert result.success is True
        assert result.total_emails == 1

        extracted_emails = [match.email for match in result.email_matches]
        assert "good@example.com" in extracted_emails
        assert "bad@spam.com" not in extracted_emails
        assert "temp@temporary.com" not in extracted_emails

    def test_email_extraction_excludes_patterns(self, extractor):
        """Test that excluded patterns are filtered out"""
        text = """
        Valid email: contact@example.com
        No reply: noreply@example.com
        Also no reply: no-reply@example.com
        """

        result = extractor.extract_from_text(text, source_url="https://example.com")

        assert result.success is True
        assert result.total_emails == 1

        extracted_emails = [match.email for match in result.email_matches]
        assert "contact@example.com" in extracted_emails
        assert "noreply@example.com" not in extracted_emails
        assert "no-reply@example.com" not in extracted_emails

    def test_email_extraction_confidence_filtering(self, extractor):
        """Test that low confidence emails are filtered out"""
        # Mock the confidence calculation to return different values
        with patch.object(extractor, '_calculate_confidence') as mock_confidence:
            mock_confidence.side_effect = [0.9, 0.6, 0.8]  # high, low, medium

            text = "Email1: high@example.com, Email2: low@example.com, Email3: medium@example.com"
            result = extractor.extract_from_text(text, source_url="https://example.com")

            # Should only include emails with confidence >= 0.8
            assert result.total_emails == 2
            extracted_emails = [match.email for match in result.email_matches]
            assert "high@example.com" in extracted_emails
            assert "medium@example.com" in extracted_emails
            assert "low@example.com" not in extracted_emails

    def test_extract_from_html(self, extractor):
        """Test email extraction from HTML content"""
        html_content = """
        <html>
            <body>
                <p>Contact us at <a href="mailto:contact@example.com">contact@example.com</a></p>
                <div>Support: support@example.com</div>
                <!-- Hidden comment: hidden@example.com -->
                <script>var email = "script@example.com";</script>
            </body>
        </html>
        """

        result = extractor.extract_from_html(html_content, source_url="https://example.com")

        assert result.success is True
        assert result.total_emails >= 2  # At least contact and support emails

        extracted_emails = [match.email for match in result.email_matches]
        assert "contact@example.com" in extracted_emails
        assert "support@example.com" in extracted_emails
        # Should also find emails in comments and scripts
        assert "hidden@example.com" in extracted_emails
        assert "script@example.com" in extracted_emails

    def test_extract_emails_from_links(self, extractor):
        """Test extraction of emails from mailto links"""
        html_content = """
        <html>
            <body>
                <a href="mailto:contact@example.com">Contact Us</a>
                <a href="mailto:support@example.com?subject=Help">Get Support</a>
                <a href="mailto:sales@example.com?subject=Inquiry&body=Hello">Sales</a>
            </body>
        </html>
        """

        result = extractor.extract_from_html(html_content, source_url="https://example.com")

        assert result.success is True
        assert result.total_emails >= 3

        extracted_emails = [match.email for match in result.email_matches]
        assert "contact@example.com" in extracted_emails
        assert "support@example.com" in extracted_emails
        assert "sales@example.com" in extracted_emails

    def test_duplicate_email_handling(self, extractor):
        """Test that duplicate emails are handled correctly"""
        text = """
        Primary contact: support@example.com
        Backup contact: support@example.com
        Alternative: support@example.com
        """

        result = extractor.extract_from_text(text, source_url="https://example.com")

        # Should find multiple instances but count unique emails
        assert result.success is True
        assert len(result.email_matches) == 3  # All instances found
        assert result.total_emails == 3  # But unique count might be different

        # All matches should be the same email
        assert all(match.email == "support@example.com" for match in result.email_matches)

    def test_complex_email_patterns(self, extractor):
        """Test extraction of complex email patterns"""
        text = """
        Standard: user@domain.com
        Subdomain: user@mail.domain.com
        Hyphenated: user-name@domain-name.com
        Numbers: user123@domain456.com
        Plus addressing: user+tag@domain.com
        Dots: first.last@domain.co.uk
        """

        result = extractor.extract_from_text(text, source_url="https://example.com")

        assert result.success is True
        assert result.total_emails == 6

        extracted_emails = [match.email for match in result.email_matches]
        assert "user@domain.com" in extracted_emails
        assert "user@mail.domain.com" in extracted_emails
        assert "user-name@domain-name.com" in extracted_emails
        assert "user123@domain456.com" in extracted_emails
        assert "user+tag@domain.com" in extracted_emails
        assert "first.last@domain.co.uk" in extracted_emails

    def test_invalid_email_patterns(self, extractor):
        """Test that invalid email patterns are not extracted"""
        text = """
        Invalid emails:
        @domain.com
        user@
        user@@domain.com
        user@domain
        user@.com
        user@domain.
        """

        result = extractor.extract_from_text(text, source_url="https://example.com")

        # Should not extract any emails (all are invalid)
        assert result.success is True
        assert result.total_emails == 0

    def test_calculate_confidence(self, extractor):
        """Test confidence calculation for email matches"""
        # Test high confidence (common business email)
        high_conf = extractor._calculate_confidence("contact@company.com", "Contact us at contact@company.com")
        assert high_conf > 0.8

        # Test medium confidence (personal email)
        med_conf = extractor._calculate_confidence("john.doe@gmail.com", "Personal email: john.doe@gmail.com")
        assert 0.5 <= med_conf <= 0.8

        # Test lower confidence (suspicious pattern)
        low_conf = extractor._calculate_confidence("x@y.z", "Some text x@y.z here")
        assert low_conf < 0.7

    def test_extract_context(self, extractor):
        """Test context extraction around email matches"""
        text = "This is a long sentence with contact@example.com in the middle of it for testing purposes."

        context = extractor._extract_context(text, 25, 43)  # Position of email

        assert "contact@example.com" in context
        assert len(context) <= extractor.max_context_chars
        assert "long sentence" in context
        assert "middle of it" in context

    def test_is_valid_email(self, extractor):
        """Test email validation"""
        # Valid emails
        assert extractor._is_valid_email("user@domain.com") is True
        assert extractor._is_valid_email("first.last@subdomain.domain.co.uk") is True
        assert extractor._is_valid_email("user+tag@domain.com") is True
        assert extractor._is_valid_email("user123@domain456.com") is True

        # Invalid emails
        assert extractor._is_valid_email("") is False
        assert extractor._is_valid_email("@domain.com") is False
        assert extractor._is_valid_email("user@") is False
        assert extractor._is_valid_email("user@@domain.com") is False
        assert extractor._is_valid_email("user@domain") is False
        assert extractor._is_valid_email("user@.com") is False

    def test_extract_from_empty_content(self, extractor):
        """Test extraction from empty or None content"""
        # Empty string
        result = extractor.extract_from_text("", source_url="https://example.com")
        assert result.success is True
        assert result.total_emails == 0

        # None content should handle gracefully
        result = extractor.extract_from_text(None, source_url="https://example.com")
        assert result.success is False
        assert "No content provided" in result.error

    def test_extract_with_large_content(self, extractor):
        """Test extraction from very large content"""
        # Create large text with scattered emails
        large_text = "Start text. " * 1000
        large_text += "contact@example.com"
        large_text += " Middle text. " * 1000
        large_text += "support@example.com"
        large_text += " End text. " * 1000

        result = extractor.extract_from_text(large_text, source_url="https://example.com")

        assert result.success is True
        assert result.total_emails == 2
        assert result.extraction_time > 0

        extracted_emails = [match.email for match in result.email_matches]
        assert "contact@example.com" in extracted_emails
        assert "support@example.com" in extracted_emails

    def test_domain_classification(self, extractor):
        """Test domain classification for confidence scoring"""
        # Business domains should have higher confidence
        business_match = EmailMatch(
            email="contact@company.com",
            domain="company.com",
            local_part="contact"
        )

        # Personal domains should have lower confidence
        personal_match = EmailMatch(
            email="user@gmail.com",
            domain="gmail.com",
            local_part="user"
        )

        # Test that business emails get higher confidence
        business_conf = extractor._calculate_confidence(business_match.email, "Contact: contact@company.com")
        personal_conf = extractor._calculate_confidence(personal_match.email, "Personal: user@gmail.com")

        # Business should typically have higher confidence than personal
        # Note: This depends on the actual implementation logic
        assert business_conf >= personal_conf or abs(business_conf - personal_conf) < 0.1