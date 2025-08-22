"""
Unit tests for data enrichment functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from datetime import datetime, timedelta

from enrich.enricher import DataEnricher, EnrichmentResult, EnrichmentSource, CompanyInfo, SocialProfile
from core.database import Contact, ContactStatus


class TestCompanyInfo:
    """Test CompanyInfo dataclass"""

    def test_company_info_creation(self):
        """Test creating company information"""
        company = CompanyInfo(
            name="TechCorp Inc",
            domain="techcorp.com",
            industry="Technology",
            size="100-500",
            location="San Francisco, CA",
            description="Leading technology company",
            founded_year=2010,
            revenue="$10M-50M",
            employee_count=250,
            website="https://techcorp.com"
        )

        assert company.name == "TechCorp Inc"
        assert company.domain == "techcorp.com"
        assert company.industry == "Technology"
        assert company.size == "100-500"
        assert company.location == "San Francisco, CA"
        assert company.description == "Leading technology company"
        assert company.founded_year == 2010
        assert company.revenue == "$10M-50M"
        assert company.employee_count == 250
        assert company.website == "https://techcorp.com"

    def test_company_info_defaults(self):
        """Test company info with default values"""
        company = CompanyInfo(
            name="Test Company",
            domain="test.com"
        )

        assert company.name == "Test Company"
        assert company.domain == "test.com"
        assert company.industry is None
        assert company.size is None
        assert company.location is None
        assert company.description is None
        assert company.founded_year is None
        assert company.revenue is None
        assert company.employee_count is None
        assert company.website is None


class TestSocialProfile:
    """Test SocialProfile dataclass"""

    def test_social_profile_creation(self):
        """Test creating social profile"""
        profile = SocialProfile(
            platform="linkedin",
            url="https://linkedin.com/in/john-doe",
            username="john-doe",
            followers=1250,
            verified=True,
            profile_data={"title": "CTO", "connections": 500}
        )

        assert profile.platform == "linkedin"
        assert profile.url == "https://linkedin.com/in/john-doe"
        assert profile.username == "john-doe"
        assert profile.followers == 1250
        assert profile.verified is True
        assert profile.profile_data["title"] == "CTO"

    def test_social_profile_defaults(self):
        """Test social profile with defaults"""
        profile = SocialProfile(
            platform="twitter",
            url="https://twitter.com/user"
        )

        assert profile.platform == "twitter"
        assert profile.url == "https://twitter.com/user"
        assert profile.username is None
        assert profile.followers == 0
        assert profile.verified is False
        assert profile.profile_data == {}


class TestEnrichmentSource:
    """Test EnrichmentSource enum"""

    def test_enrichment_source_values(self):
        """Test enrichment source enumeration values"""
        assert EnrichmentSource.CLEARBIT.value == "clearbit"
        assert EnrichmentSource.HUNTER.value == "hunter"
        assert EnrichmentSource.LINKEDIN.value == "linkedin"
        assert EnrichmentSource.COMPANY_WEBSITE.value == "company_website"
        assert EnrichmentSource.SOCIAL_MEDIA.value == "social_media"


class TestEnrichmentResult:
    """Test EnrichmentResult dataclass"""

    def test_enrichment_result_creation(self):
        """Test creating enrichment result"""
        company_info = CompanyInfo(name="Test Corp", domain="test.com")
        social_profiles = [
            SocialProfile(platform="linkedin", url="https://linkedin.com/company/test"),
            SocialProfile(platform="twitter", url="https://twitter.com/testcorp")
        ]

        result = EnrichmentResult(
            contact_email="cto@test.com",
            company_info=company_info,
            social_profiles=social_profiles,
            additional_emails=["contact@test.com", "info@test.com"],
            phone_numbers=["+1-555-0123"],
            sources_used=[EnrichmentSource.CLEARBIT, EnrichmentSource.LINKEDIN],
            confidence_score=0.85,
            enrichment_time=2.5,
            success=True
        )

        assert result.contact_email == "cto@test.com"
        assert result.company_info.name == "Test Corp"
        assert len(result.social_profiles) == 2
        assert len(result.additional_emails) == 2
        assert len(result.phone_numbers) == 1
        assert len(result.sources_used) == 2
        assert result.confidence_score == 0.85
        assert result.enrichment_time == 2.5
        assert result.success is True
        assert result.error is None
        assert result.timestamp is not None

    def test_enrichment_result_with_error(self):
        """Test enrichment result with error"""
        result = EnrichmentResult(
            contact_email="test@example.com",
            success=False,
            error="API rate limit exceeded"
        )

        assert result.contact_email == "test@example.com"
        assert result.success is False
        assert result.error == "API rate limit exceeded"
        assert result.company_info is None
        assert result.social_profiles == []
        assert result.additional_emails == []
        assert result.sources_used == []


class TestDataEnricher:
    """Test DataEnricher class"""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        config = {
            "clearbit_api_key": "test_clearbit_key",
            "hunter_api_key": "test_hunter_key",
            "linkedin_access_token": "test_linkedin_token",
            "rate_limit_delay": 1.0,
            "max_retries": 3,
            "timeout": 30
        }
        return config

    @pytest.fixture
    def enricher(self, mock_config):
        """Create DataEnricher instance for testing"""
        return DataEnricher(config=mock_config)

    def test_enricher_initialization(self, enricher, mock_config):
        """Test enricher initialization"""
        assert enricher.config == mock_config
        assert enricher.rate_limit_delay == 1.0
        assert enricher.max_retries == 3
        assert enricher.timeout == 30
        assert enricher.session is not None

    def test_enricher_default_initialization(self):
        """Test enricher with default configuration"""
        enricher = DataEnricher()
        assert enricher.config == {}
        assert enricher.rate_limit_delay == 2.0
        assert enricher.max_retries == 3
        assert enricher.timeout == 30

    @patch('requests.Session.get')
    def test_enrich_contact_clearbit_success(self, mock_get, enricher):
        """Test successful contact enrichment using Clearbit"""
        # Mock Clearbit API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "person": {
                "name": {"fullName": "John Doe"},
                "employment": {"title": "CTO", "name": "TechCorp"}
            },
            "company": {
                "name": "TechCorp Inc",
                "domain": "techcorp.com",
                "category": {"industry": "Technology"},
                "metrics": {"employees": 250},
                "geo": {"city": "San Francisco", "state": "CA"}
            }
        }
        mock_get.return_value = mock_response

        contact = Contact(email="john@techcorp.com", domain="techcorp.com")
        result = enricher.enrich_contact(contact)

        assert result.success is True
        assert result.contact_email == "john@techcorp.com"
        assert result.company_info is not None
        assert result.company_info.name == "TechCorp Inc"
        assert result.company_info.industry == "Technology"
        assert EnrichmentSource.CLEARBIT in result.sources_used

    @patch('requests.Session.get')
    def test_enrich_contact_clearbit_not_found(self, mock_get, enricher):
        """Test contact enrichment when Clearbit returns no data"""
        # Mock Clearbit API response - not found
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        contact = Contact(email="unknown@example.com", domain="example.com")
        result = enricher.enrich_contact(contact)

        # Should still try other sources and return partial results
        assert result.contact_email == "unknown@example.com"
        # Success might be False if no data found from any source

    @patch('requests.Session.get')
    def test_enrich_contact_api_error(self, mock_get, enricher):
        """Test contact enrichment with API error"""
        # Mock API error
        mock_get.side_effect = requests.exceptions.RequestException("API Error")

        contact = Contact(email="test@company.com", domain="company.com")
        result = enricher.enrich_contact(contact)

        assert result.success is False
        assert "API Error" in result.error

    @patch('requests.Session.get')
    def test_enrich_from_clearbit(self, mock_get, enricher):
        """Test enrichment specifically from Clearbit"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "person": {"name": {"fullName": "Jane Smith"}},
            "company": {
                "name": "Enterprise Corp",
                "domain": "enterprise.com",
                "category": {"industry": "Finance"},
                "metrics": {"employees": 500}
            }
        }
        mock_get.return_value = mock_response

        company_info, additional_data = enricher._enrich_from_clearbit("jane@enterprise.com")

        assert company_info is not None
        assert company_info.name == "Enterprise Corp"
        assert company_info.domain == "enterprise.com"
        assert company_info.industry == "Finance"
        assert company_info.employee_count == 500

    @patch('requests.Session.get')
    def test_enrich_from_hunter(self, mock_get, enricher):
        """Test enrichment from Hunter.io"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "organization": "Hunter Corp",
                "emails": [
                    {"value": "contact@hunter.com", "type": "generic"},
                    {"value": "sales@hunter.com", "type": "generic"}
                ]
            }
        }
        mock_get.return_value = mock_response

        emails, company_data = enricher._enrich_from_hunter("test@hunter.com")

        assert len(emails) == 2
        assert "contact@hunter.com" in emails
        assert "sales@hunter.com" in emails
        assert company_data["organization"] == "Hunter Corp"

    @patch('requests.Session.get')
    def test_enrich_from_company_website(self, mock_get, enricher):
        """Test enrichment from company website"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head><title>TechCorp - Leading Technology Solutions</title></head>
            <body>
                <h1>About TechCorp</h1>
                <p>Founded in 2010, TechCorp is a leading technology company.</p>
                <p>Contact us: info@techcorp.com, support@techcorp.com</p>
                <p>Phone: +1-555-0123</p>
            </body>
        </html>
        """
        mock_get.return_value = mock_response

        website_data = enricher._enrich_from_company_website("techcorp.com")

        assert website_data is not None
        assert "emails" in website_data
        assert "info@techcorp.com" in website_data["emails"]
        assert "support@techcorp.com" in website_data["emails"]
        assert "phones" in website_data
        assert "+1-555-0123" in website_data["phones"]

    def test_extract_company_info_from_clearbit(self, enricher):
        """Test extracting company info from Clearbit data"""
        clearbit_data = {
            "company": {
                "name": "Test Company",
                "domain": "test.com",
                "category": {"industry": "Software"},
                "description": "A test company",
                "foundedYear": 2015,
                "metrics": {"employees": 100, "estimatedAnnualRevenue": "10000000"},
                "geo": {"city": "Boston", "state": "MA", "country": "US"},
                "site": {"url": "https://test.com"}
            }
        }

        company_info = enricher._extract_company_info_from_clearbit(clearbit_data)

        assert company_info.name == "Test Company"
        assert company_info.domain == "test.com"
        assert company_info.industry == "Software"
        assert company_info.description == "A test company"
        assert company_info.founded_year == 2015
        assert company_info.employee_count == 100
        assert company_info.location == "Boston, MA, US"
        assert company_info.website == "https://test.com"

    def test_extract_social_profiles_from_clearbit(self, enricher):
        """Test extracting social profiles from Clearbit data"""
        clearbit_data = {
            "company": {
                "linkedin": {"handle": "test-company"},
                "twitter": {"handle": "testcompany", "followers": 5000},
                "facebook": {"handle": "testcompany"}
            }
        }

        profiles = enricher._extract_social_profiles_from_clearbit(clearbit_data)

        assert len(profiles) == 3

        linkedin_profile = next((p for p in profiles if p.platform == "linkedin"), None)
        assert linkedin_profile is not None
        assert linkedin_profile.username == "test-company"

        twitter_profile = next((p for p in profiles if p.platform == "twitter"), None)
        assert twitter_profile is not None
        assert twitter_profile.username == "testcompany"
        assert twitter_profile.followers == 5000

    def test_extract_emails_from_text(self, enricher):
        """Test email extraction from text content"""
        text = """
        Contact us at info@company.com for general inquiries.
        For sales, reach out to sales@company.com.
        Support is available at support@company.com.
        Invalid email: not-an-email
        """

        emails = enricher._extract_emails_from_text(text)

        assert len(emails) == 3
        assert "info@company.com" in emails
        assert "sales@company.com" in emails
        assert "support@company.com" in emails
        assert "not-an-email" not in emails

    def test_extract_phones_from_text(self, enricher):
        """Test phone number extraction from text content"""
        text = """
        Call us at +1-555-123-4567 or (555) 987-6543.
        International: +44 20 1234 5678
        Invalid: not-a-phone
        """

        phones = enricher._extract_phones_from_text(text)

        assert len(phones) >= 2
        assert any("+1-555-123-4567" in phone or "555-123-4567" in phone for phone in phones)
        assert any("555-987-6543" in phone or "(555) 987-6543" in phone for phone in phones)

    def test_calculate_confidence_score(self, enricher):
        """Test confidence score calculation"""
        # High confidence - multiple sources, complete data
        result_high = EnrichmentResult(
            contact_email="test@company.com",
            company_info=CompanyInfo(name="Company", domain="company.com", industry="Tech"),
            social_profiles=[SocialProfile(platform="linkedin", url="test")],
            additional_emails=["info@company.com"],
            sources_used=[EnrichmentSource.CLEARBIT, EnrichmentSource.HUNTER],
            success=True
        )

        confidence_high = enricher._calculate_confidence_score(result_high)
        assert confidence_high > 0.7

        # Low confidence - single source, minimal data
        result_low = EnrichmentResult(
            contact_email="test@unknown.com",
            company_info=CompanyInfo(name="Unknown", domain="unknown.com"),
            sources_used=[EnrichmentSource.COMPANY_WEBSITE],
            success=True
        )

        confidence_low = enricher._calculate_confidence_score(result_low)
        assert confidence_low < 0.6

    def test_enrich_batch_contacts(self, enricher):
        """Test batch enrichment of multiple contacts"""
        contacts = [
            Contact(email="cto@company1.com", domain="company1.com"),
            Contact(email="ceo@company2.com", domain="company2.com"),
            Contact(email="dev@company3.com", domain="company3.com")
        ]

        with patch.object(enricher, 'enrich_contact') as mock_enrich:
            # Mock successful enrichment for all contacts
            mock_enrich.side_effect = [
                EnrichmentResult(contact_email=c.email, success=True) for c in contacts
            ]

            results = enricher.enrich_batch(contacts)

            assert len(results) == 3
            assert all(result.success for result in results)
            assert mock_enrich.call_count == 3

    def test_enrich_batch_with_rate_limiting(self, enricher):
        """Test batch enrichment respects rate limiting"""
        enricher.rate_limit_delay = 0.1  # Short delay for testing

        contacts = [
            Contact(email="test1@company.com"),
            Contact(email="test2@company.com")
        ]

        with patch.object(enricher, 'enrich_contact') as mock_enrich, \
             patch('time.sleep') as mock_sleep:

            mock_enrich.return_value = EnrichmentResult(contact_email="test", success=True)

            start_time = datetime.now()
            results = enricher.enrich_batch(contacts)
            end_time = datetime.now()

            # Should have called sleep for rate limiting
            assert mock_sleep.called
            assert len(results) == 2

    def test_get_api_headers(self, enricher):
        """Test API header generation"""
        headers = enricher._get_api_headers("clearbit")
        assert "Authorization" in headers
        assert enricher.config["clearbit_api_key"] in headers["Authorization"]

        headers = enricher._get_api_headers("hunter")
        assert "Authorization" in headers
        assert enricher.config["hunter_api_key"] in headers["Authorization"]

    def test_handle_rate_limiting(self, enricher):
        """Test rate limiting handling"""
        with patch('time.sleep') as mock_sleep:
            enricher._handle_rate_limiting()
            mock_sleep.assert_called_once_with(enricher.rate_limit_delay)

    def test_retry_on_failure(self, enricher):
        """Test retry mechanism on API failures"""
        with patch('requests.Session.get') as mock_get:
            # First two calls fail, third succeeds
            mock_get.side_effect = [
                requests.exceptions.ConnectionError("Connection failed"),
                requests.exceptions.Timeout("Timeout"),
                Mock(status_code=200, json=lambda: {"data": "success"})
            ]

            contact = Contact(email="test@company.com")
            result = enricher.enrich_contact(contact)

            # Should have retried and eventually succeeded
            assert mock_get.call_count == 3

    def test_validate_api_keys(self, enricher):
        """Test API key validation"""
        # Should have API keys from mock config
        assert enricher._validate_api_keys() is True

        # Test with missing keys
        enricher_no_keys = DataEnricher(config={})
        assert enricher_no_keys._validate_api_keys() is False

    def test_clean_phone_number(self, enricher):
        """Test phone number cleaning"""
        assert enricher._clean_phone_number("+1-555-123-4567") == "+15551234567"
        assert enricher._clean_phone_number("(555) 123-4567") == "5551234567"
        assert enricher._clean_phone_number("555.123.4567") == "5551234567"

    def test_normalize_company_name(self, enricher):
        """Test company name normalization"""
        assert enricher._normalize_company_name("TechCorp Inc.") == "TechCorp Inc"
        assert enricher._normalize_company_name("Company LLC") == "Company LLC"
        assert enricher._normalize_company_name("Corp., Ltd.") == "Corp., Ltd"

    def test_detect_industry_from_domain(self, enricher):
        """Test industry detection from domain"""
        assert enricher._detect_industry_from_domain("bank.com") == "Finance"
        assert enricher._detect_industry_from_domain("tech.com") == "Technology"
        assert enricher._detect_industry_from_domain("unknown.com") == "Other"

    def test_enrichment_result_serialization(self, enricher):
        """Test that enrichment results can be serialized"""
        result = EnrichmentResult(
            contact_email="test@company.com",
            company_info=CompanyInfo(name="Test Co", domain="test.com"),
            success=True
        )

        # Should be able to convert to dict for storage
        result_dict = enricher._serialize_result(result)
        assert isinstance(result_dict, dict)
        assert result_dict["contact_email"] == "test@company.com"
        assert result_dict["success"] is True
        assert "company_info" in result_dict