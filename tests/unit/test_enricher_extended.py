"""
Extended coverage tests for enrich/enricher.py
Targets uncovered lines: 144-145, 165, 169-171, 187-199, 237-238, 242-243,
265-266, 281-282, 328, 357, 373-396, 402-413, 427, 431-440, 508-545, 555-578,
583-593, 598-610, 615-619, 629-646, 658-666, 671-715
"""
import pytest
from unittest.mock import MagicMock, patch, call

from enrich.enricher import (
    DataEnricher, CompanyInfo, EnrichmentResult, EnrichmentSource, SocialProfile
)
from core.database import Contact, ContactStatus


def make_enricher(config=None, db=None):
    cfg = config if config is not None else {
        "clearbit_api_key": "ck_test",
        "hunter_api_key": "hk_test",
    }
    return DataEnricher(config=cfg, db_manager=db)


def make_contact(email="ceo@example.com", domain="example.com"):
    c = Contact(
        email=email, domain=domain, name=None, role=None,
        company=None, confidence_score=0.8, source_url=None,
        source="crawler", status=ContactStatus.UNVALIDATED,
    )
    return c


# ── _get_api_headers ────────────────────────────────────────────────────────

class TestGetApiHeaders:
    def test_clearbit_includes_key(self):
        e = make_enricher()
        h = e._get_api_headers("clearbit")
        assert "Authorization" in h
        assert "ck_test" in h["Authorization"]

    def test_hunter_includes_key(self):
        e = make_enricher()
        h = e._get_api_headers("hunter")
        assert "Authorization" in h
        assert "hk_test" in h["Authorization"]

    def test_unknown_api_returns_empty_bearer(self):
        """Line 357: fallback branch for unknown API name."""
        e = make_enricher()
        h = e._get_api_headers("unknown_api")
        assert h == {"Authorization": "Bearer "}

    def test_linkedin_returns_empty_bearer(self):
        # linkedin is not a known API key in _get_api_headers → same fallback
        e = make_enricher(config={"linkedin_access_token": "lt_token"})
        h = e._get_api_headers("linkedin")
        assert h == {"Authorization": "Bearer "}


# ── _extract_phones_from_text / tuple normalization ─────────────────────────

class TestExtractPhonesFromText:
    def test_tuple_normalization_branch(self):
        """Line 328: phones list with tuple entries is normalised to strings."""
        e = make_enricher()
        text = "Reach us at +1-800-555-1234 or (555) 987-6543 ext.101"
        phones = e._extract_phones_from_text(text)
        # All results must be strings (not tuples)
        for p in phones:
            assert isinstance(p, str)

    def test_no_phones_returns_empty(self):
        e = make_enricher()
        assert e._extract_phones_from_text("No numbers here at all.") == []

    def test_international_number(self):
        e = make_enricher()
        phones = e._extract_phones_from_text("+47 98765432")
        assert len(phones) >= 1


# ── _validate_api_keys ───────────────────────────────────────────────────────

class TestValidateApiKeys:
    def test_with_clearbit_key(self):
        e = make_enricher(config={"clearbit_api_key": "ck"})
        assert e._validate_api_keys() is True

    def test_empty_config(self):
        e = make_enricher(config={})
        assert e._validate_api_keys() is False


# ── _normalize_company_name / _detect_industry_from_domain ─────────────────

class TestUtilityMethods:
    def test_normalize_removes_trailing_dot(self):
        e = make_enricher()
        assert e._normalize_company_name("Acme Corp.") == "Acme Corp"

    def test_normalize_no_trailing_dot(self):
        e = make_enricher()
        assert e._normalize_company_name("Acme Corp") == "Acme Corp"

    def test_industry_bank(self):
        e = make_enricher()
        assert e._detect_industry_from_domain("mybank.com") == "Finance"

    def test_industry_tech(self):
        e = make_enricher()
        assert e._detect_industry_from_domain("techstartup.io") == "Technology"

    def test_industry_software(self):
        e = make_enricher()
        assert e._detect_industry_from_domain("software.dev") == "Technology"

    def test_industry_other(self):
        e = make_enricher()
        assert e._detect_industry_from_domain("randomshop.com") == "Other"

    def test_clean_phone_with_plus(self):
        e = make_enricher()
        result = e._clean_phone_number("+1 (800) 555-1234")
        assert result.startswith("+")
        assert result == "+18005551234"

    def test_clean_phone_without_plus(self):
        e = make_enricher()
        result = e._clean_phone_number("(800) 555-1234")
        assert result == "8005551234"


# ── _serialize_result ────────────────────────────────────────────────────────

class TestSerializeResult:
    def test_serialize_success_result(self):
        e = make_enricher()
        r = EnrichmentResult(contact_email="x@example.com", success=True,
                             company_info=CompanyInfo(name="Acme", domain="acme.com"))
        data = e._serialize_result(r)
        assert data["contact_email"] == "x@example.com"
        assert data["success"] is True
        assert data["company_info"]["name"] == "Acme"

    def test_serialize_no_company_info(self):
        e = make_enricher()
        r = EnrichmentResult(contact_email="y@example.com", success=False)
        data = e._serialize_result(r)
        assert data["company_info"] is None


# ── _retry_on_failure ────────────────────────────────────────────────────────

class TestRetryOnFailure:
    """Lines 431-440: _retry_on_failure body."""

    def test_succeeds_on_first_call(self):
        e = make_enricher()
        func = MagicMock(return_value="ok")
        result = e._retry_on_failure(func, "arg")
        assert result == "ok"
        func.assert_called_once_with("arg")

    def test_returns_none_after_all_retries_fail(self):
        e = make_enricher()
        e.max_retries = 2
        func = MagicMock(side_effect=Exception("timeout"))
        result = e._retry_on_failure(func)
        assert result is None
        assert func.call_count == 2

    def test_succeeds_on_second_retry(self):
        e = make_enricher()
        e.max_retries = 3
        func = MagicMock(side_effect=[Exception("first"), "success"])
        result = e._retry_on_failure(func)
        assert result == "success"


# ── _estimate_company_size ───────────────────────────────────────────────────

class TestEstimateCompanySize:
    """Lines 508-545: _estimate_company_size method."""

    def test_enterprise_domain_indicator(self):
        e = make_enricher()
        result = e._estimate_company_size({
            "name": "Corp", "domain": "corp-global-intl.com", "industry": "finance"
        })
        assert "estimated_size_category" in result
        assert "estimated_employee_range" in result
        assert "size_confidence" in result

    def test_startup_indicator_in_name(self):
        e = make_enricher()
        result = e._estimate_company_size({
            "name": "seed startup inc", "domain": "freshstart.io", "industry": "startup seed series a"
        })
        assert result["estimated_size_category"] in ("startup", "scale_up", "sme", "enterprise")

    def test_empty_company(self):
        e = make_enricher()
        result = e._estimate_company_size({})
        assert "estimated_size_category" in result

    def test_size_indicators_found_in_result(self):
        e = make_enricher()
        result = e._estimate_company_size({"name": "enterprise global", "domain": "x.com", "industry": ""})
        assert "size_indicators_found" in result


# ── _enrich_with_external_apis ──────────────────────────────────────────────

class TestEnrichWithExternalApis:
    """Lines 555-578: _enrich_with_external_apis."""

    def test_no_domain_returns_empty(self):
        e = make_enricher()
        result = e._enrich_with_external_apis({"name": "NoDomainCo"})
        assert result == {}

    def test_with_domain_returns_enrichment_data(self):
        e = make_enricher()
        result = e._enrich_with_external_apis({
            "name": "TechCo", "domain": "techco.com", "industry": "technology"
        })
        assert "employee_count_estimate" in result
        assert "annual_revenue_estimate" in result
        assert "social_media_presence" in result
        assert "funding_information" in result

    def test_exception_in_simulate_returns_empty(self):
        e = make_enricher()
        with patch.object(e, "_simulate_employee_count", side_effect=Exception("sim error")):
            result = e._enrich_with_external_apis({
                "name": "X", "domain": "x.com", "industry": "retail"
            })
        # Exception caught gracefully → returns empty dict
        assert isinstance(result, dict)


# ── _simulate_employee_count ─────────────────────────────────────────────────

class TestSimulateEmployeeCount:
    """Lines 583-593: _simulate_employee_count."""

    def test_technology_industry(self):
        e = make_enricher()
        assert e._simulate_employee_count({"industry": "technology"}) == 150

    def test_ecommerce_industry(self):
        e = make_enricher()
        assert e._simulate_employee_count({"industry": "ecommerce"}) == 75

    def test_manufacturing_industry(self):
        e = make_enricher()
        assert e._simulate_employee_count({"industry": "manufacturing"}) == 300

    def test_default_industry(self):
        e = make_enricher()
        assert e._simulate_employee_count({"industry": "retail"}) == 100

    def test_empty_company(self):
        e = make_enricher()
        assert e._simulate_employee_count({}) == 100


# ── _simulate_revenue_estimate ───────────────────────────────────────────────

class TestSimulateRevenueEstimate:
    """Lines 598-610: _simulate_revenue_estimate."""

    def test_tech_revenue(self):
        e = make_enricher()
        rev = e._simulate_revenue_estimate({"industry": "technology"})
        assert rev is not None
        assert "$" in rev

    def test_small_company_revenue(self):
        # Force small employee count
        e = make_enricher()
        with patch.object(e, "_simulate_employee_count", return_value=30):
            rev = e._simulate_revenue_estimate({})
        assert rev == "$1M-$10M"

    def test_medium_company_revenue(self):
        e = make_enricher()
        with patch.object(e, "_simulate_employee_count", return_value=100):
            rev = e._simulate_revenue_estimate({})
        assert rev == "$10M-$50M"

    def test_large_company_revenue(self):
        e = make_enricher()
        with patch.object(e, "_simulate_employee_count", return_value=300):
            rev = e._simulate_revenue_estimate({})
        assert rev == "$50M-$200M"

    def test_enterprise_revenue(self):
        e = make_enricher()
        with patch.object(e, "_simulate_employee_count", return_value=1000):
            rev = e._simulate_revenue_estimate({})
        assert rev == "$200M+"

    def test_none_employee_count_returns_none(self):
        e = make_enricher()
        with patch.object(e, "_simulate_employee_count", return_value=None):
            rev = e._simulate_revenue_estimate({})
        assert rev is None


# ── _simulate_social_presence ─────────────────────────────────────────────────

class TestSimulateSocialPresence:
    """Lines 615-619: _simulate_social_presence."""

    def test_returns_social_urls(self):
        e = make_enricher()
        result = e._simulate_social_presence({"name": "Acme Corp", "domain": "acme.com"})
        assert "linkedin" in result
        assert "twitter" in result
        assert "facebook" in result
        assert result["has_social_presence"] is True

    def test_company_name_lower_in_urls(self):
        e = make_enricher()
        result = e._simulate_social_presence({"name": "My Company", "domain": "myco.com"})
        assert "mycompany" in result["linkedin"]


# ── _simulate_funding_info ────────────────────────────────────────────────────

class TestSimulateFundingInfo:
    """Lines 629-646: _simulate_funding_info."""

    def test_technology_funding(self):
        e = make_enricher()
        info = e._simulate_funding_info({"industry": "technology"})
        assert info["funding_stage"] == "Series B"
        assert info["total_funding"] == "$25M"

    def test_startup_funding(self):
        e = make_enricher()
        info = e._simulate_funding_info({"industry": "startup"})
        assert info["funding_stage"] == "Seed"

    def test_other_industry_funding(self):
        e = make_enricher()
        info = e._simulate_funding_info({"industry": "retail"})
        assert info["funding_stage"] == "Unknown"
        assert info["investors_count"] == 0

    def test_none_last_funding_date_in_other(self):
        e = make_enricher()
        info = e._simulate_funding_info({"industry": "logistics"})
        assert info["last_funding_date"] is None


# ── _update_company_enrichment ────────────────────────────────────────────────

class TestUpdateCompanyEnrichment:
    """Lines 658-666: _update_company_enrichment."""

    def test_with_cache_set_method(self):
        db = MagicMock()
        db.cache_set = MagicMock()
        e = make_enricher(db=db)
        e._update_company_enrichment(42, {"tech": ["React"]})
        db.cache_set.assert_called_once()
        call_args = db.cache_set.call_args[0]
        assert "enrichment:42" in call_args[0]

    def test_cache_set_raises_no_error(self):
        db = MagicMock()
        db.cache_set = MagicMock(side_effect=Exception("cache error"))
        e = make_enricher(db=db)
        # Should not propagate the exception
        e._update_company_enrichment(1, {})

    def test_db_manager_without_cache_set(self):
        db = MagicMock(spec=[])  # No methods
        e = make_enricher(db=db)
        # Should log debug and not raise
        e._update_company_enrichment(1, {"key": "val"})

    def test_no_db_manager(self):
        e = make_enricher(db=None)
        # Should log debug and not raise
        e._update_company_enrichment(1, {})


# ── get_enrichment_statistics ─────────────────────────────────────────────────

class TestGetEnrichmentStatistics:
    """Lines 671-715: get_enrichment_statistics."""

    def test_empty_companies_gives_zero_stats(self):
        db = MagicMock()
        db.get_companies.return_value = []
        e = make_enricher(db=db)
        stats = e.get_enrichment_statistics()
        assert stats["total_companies"] == 0
        assert stats["enrichment_rate"] == 0

    def test_single_enriched_company(self):
        db = MagicMock()
        db.get_companies.return_value = [{"id": 1}]
        db.cache_get.return_value = {
            "technologies": [{"name": "React"}, {"name": "Python"}],
            "estimated_size_category": "startup"
        }
        e = make_enricher(db=db)
        stats = e.get_enrichment_statistics()
        assert stats["total_companies"] == 1
        assert stats["enriched_companies"] == 1
        assert stats["enrichment_rate"] == 100.0

    def test_mix_of_enriched_and_unenriched(self):
        db = MagicMock()
        db.get_companies.return_value = [{"id": 1}, {"id": 2}, {"id": 3}]
        db.cache_get.side_effect = lambda k: (
            {"technologies": [{"name": "Vue"}], "estimated_size_category": "enterprise"}
            if k == "enrichment:1" else None
        )
        e = make_enricher(db=db)
        stats = e.get_enrichment_statistics()
        assert stats["total_companies"] == 3
        assert stats["enriched_companies"] == 1
        assert "React" not in (stats.get("top_technologies") or {})

    def test_top_technologies_aggregated(self):
        db = MagicMock()
        db.get_companies.return_value = [{"id": 1}, {"id": 2}]
        db.cache_get.side_effect = lambda k: {
            "technologies": [{"name": "React"}],
            "estimated_size_category": "startup"
        }
        e = make_enricher(db=db)
        stats = e.get_enrichment_statistics()
        assert stats["top_technologies"].get("React", 0) >= 1


# ── enrich_all_companies ──────────────────────────────────────────────────────

class TestEnrichAllCompanies:
    """Lines 187-199: enrich_all_companies body."""

    def test_processes_all_contacts(self):
        db = MagicMock()
        contacts = [
            make_contact("a@example.com", "example.com"),
            make_contact("b@example.com", "example.com"),
        ]
        db.get_all_contacts.return_value = contacts
        e = make_enricher(db=db)
        # Mock enrich_contact to avoid network calls
        with patch.object(e, "enrich_contact", return_value=MagicMock(success=True)):
            result = e.enrich_all_companies()
        assert result["total"] == 2
        assert result["companies_processed"] == 2
        assert result["failed"] == 0

    def test_handles_enrich_failures(self):
        db = MagicMock()
        db.get_all_contacts.return_value = [make_contact()]
        e = make_enricher(db=db)
        with patch.object(e, "enrich_contact", side_effect=Exception("fail")):
            result = e.enrich_all_companies()
        assert result["failed"] == 1

    def test_empty_contacts(self):
        db = MagicMock()
        db.get_all_contacts.return_value = []
        e = make_enricher(db=db)
        result = e.enrich_all_companies()
        assert result["total"] == 0


# ── _enrich_from_clearbit with 200 response ──────────────────────────────────

class TestEnrichFromClearbit:
    """Lines 373-396: _enrich_from_clearbit 200-response processing."""

    def test_200_response_returns_company(self):
        e = make_enricher()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "company": {
                "name": "Acme Corp",
                "domain": "acme.com",
                "category": {"industry": "Technology"},
                "metrics": {"employees": 100},
            }
        }
        e.session.get = MagicMock(return_value=mock_resp)
        company_info, data = e._enrich_from_clearbit("ceo@acme.com")
        assert company_info is not None

    def test_200_response_no_company_block(self):
        """Still returns minimal CompanyInfo (no company key in JSON)."""
        e = make_enricher()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        e.session.get = MagicMock(return_value=mock_resp)
        company_info, data = e._enrich_from_clearbit("ceo@acme.com")
        assert company_info is not None  # fallback CompanyInfo created

    def test_404_response_returns_none(self):
        e = make_enricher()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        e.session.get = MagicMock(return_value=mock_resp)
        company_info, data = e._enrich_from_clearbit("x@y.com")
        assert company_info is None
        assert data == {}

    def test_all_retries_fail_returns_none_empty(self):
        """Lines 237-238, 242-243: all inner retries fail → returns (None, {})."""
        e = make_enricher()
        e.max_retries = 2
        e.session.get = MagicMock(side_effect=Exception("network error"))
        company_info, data = e._enrich_from_clearbit("x@y.com")
        assert company_info is None
        assert data == {}


# ── _enrich_from_hunter ───────────────────────────────────────────────────────

class TestEnrichFromHunter:
    """Lines 265-266, 281-282: _enrich_from_hunter paths."""

    def test_200_returns_emails(self):
        e = make_enricher()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "emails": [
                    {"value": "sales@hunter.com"},
                    {"value": "hr@hunter.com"},
                ]
            }
        }
        e.session.get = MagicMock(return_value=mock_resp)
        emails, company_data = e._enrich_from_hunter("lead@hunter.com")
        assert "sales@hunter.com" in emails

    def test_404_returns_empty_lists(self):
        e = make_enricher()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        e.session.get = MagicMock(return_value=mock_resp)
        emails, company_data = e._enrich_from_hunter("x@y.com")
        assert emails == []
        assert company_data == {}

    def test_all_retries_fail_returns_empty(self):
        """Lines 265-266: all hunter retries fail → returns ([], {})."""
        e = make_enricher()
        e.max_retries = 2
        e.session.get = MagicMock(side_effect=Exception("timeout"))
        emails, company_data = e._enrich_from_hunter("x@y.com")
        assert emails == []
        assert company_data == {}


# ── _enrich_from_rdap ─────────────────────────────────────────────────────────

class TestEnrichFromRdap:
    """Line 427: _enrich_from_rdap returns result."""

    def test_200_with_entity_returns_company(self):
        e = make_enricher()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "entities": [
                {
                    "roles": ["registrant"],
                    "vcardArray": [
                        "vcard",
                        [["fn", {}, "text", "Registrant Org Ltd"]]
                    ]
                }
            ],
            "events": [
                {"eventAction": "registration", "eventDate": "2018-03-15"}
            ]
        }
        e.session.get = MagicMock(return_value=mock_resp)
        result = e._enrich_from_rdap("example.com")
        assert result is not None

    def test_non_200_returns_none(self):
        e = make_enricher()
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        e.session.get = MagicMock(return_value=mock_resp)
        result = e._enrich_from_rdap("example.com")
        assert result is None

    def test_exception_returns_none(self):
        e = make_enricher()
        e.session.get = MagicMock(side_effect=Exception("RDAP unreachable"))
        result = e._enrich_from_rdap("example.com")
        assert result is None


# ── _enrich_from_whois ────────────────────────────────────────────────────────

class TestEnrichFromWhois:
    """Line 402: whois.whois() call."""

    def test_whois_returns_company_info(self):
        e = make_enricher()
        mock_w = MagicMock()
        mock_w.org = "Example Registrant LLC"
        mock_w.registrar = "GoDaddy"
        mock_w.creation_date = None
        mock_whois_mod = MagicMock()
        mock_whois_mod.whois.return_value = mock_w
        import sys
        with pytest.MonkeyPatch().context() as m:
            m.setitem(sys.modules, "whois", mock_whois_mod)
            result = e._enrich_from_whois("example.com")
        assert result is not None

    def test_whois_exception_returns_none(self):
        e = make_enricher()
        mock_whois_mod = MagicMock()
        mock_whois_mod.whois.side_effect = Exception("whois error")
        import sys
        with pytest.MonkeyPatch().context() as m:
            m.setitem(sys.modules, "whois", mock_whois_mod)
            result = e._enrich_from_whois("example.com")
        assert result is None


# ── enrich_domain ─────────────────────────────────────────────────────────────

class TestEnrichDomain:
    def test_rdap_success_sets_org_name(self):
        """RDAP vcard uses 'org' field (not 'fn')."""
        e = make_enricher()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "entities": [
                {
                    "roles": ["registrant"],
                    "vcardArray": [
                        "vcard",
                        [["org", {}, "text", "Registrant Org Ltd"]]
                    ]
                }
            ],
            "events": [
                {"eventAction": "registration", "eventDate": "2018"}
            ]
        }
        e.session.get = MagicMock(return_value=mock_resp)
        # Call _enrich_from_rdap directly to check it returns CompanyInfo
        result = e._enrich_from_rdap("registrar.com")
        assert result is not None
        assert result.name == "Registrant Org Ltd"

    def test_rdap_fallback_to_whois_when_name_is_domain(self):
        e = make_enricher()
        # RDAP returns empty entities → name = domain → enrich_domain falls to whois
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"entities": [], "events": []}
        e.session.get = MagicMock(return_value=mock_resp)
        import sys
        mock_w = MagicMock()
        mock_w.org = "Whois Corp"
        mock_w.creation_date = None
        mock_whois_mod = MagicMock()
        mock_whois_mod.whois.return_value = mock_w
        with pytest.MonkeyPatch().context() as m:
            m.setitem(sys.modules, "whois", mock_whois_mod)
            result = e.enrich_domain("example.com")
        # Whois Corp != example.com → returned
        assert result is not None


# ── enrich_contact edge cases ─────────────────────────────────────────────────

class TestEnrichContactEdgeCases:
    """Lines 165, 169-171: domain derivation and company_info assignment."""

    def test_hunter_emails_extend_additional(self):
        """Line 144-145: Hunter path when Clearbit returns no company_info."""
        e = make_enricher()

        def mock_get(url, **kwargs):
            resp = MagicMock()
            if "clearbit" in url:
                resp.status_code = 404  # Clearbit fails → returns (None, {})
            elif "hunter" in url:
                resp.status_code = 200
                resp.json.return_value = {
                    "data": {"emails": [{"value": "extra@example.com"}]}
                }
            else:
                resp.status_code = 404
            return resp

        e.session.get = mock_get
        contact = make_contact("ceo@example.com", "example.com")
        result = e.enrich_contact(contact)
        # Hunter path reached — additional emails list populated
        assert "extra@example.com" in result.additional_emails

    def test_domain_derived_from_email_when_no_domain_attr(self):
        """Lines 165, 169: contact has email but no domain → derive domain."""
        e = make_enricher()
        # All HTTP calls fail → falls through to enrich_domain
        e.session.get = MagicMock(side_effect=Exception("network"))

        real_company = CompanyInfo(name="RDAP Corp", domain="nodomain.com")
        with patch.object(e, "enrich_domain", return_value=real_company):
            # Contact has no domain attribute
            from unittest.mock import PropertyMock
            contact = MagicMock()
            contact.email = "boss@nodomain.com"
            contact.domain = None
            result = e.enrich_contact(contact)
        # company_info should be assigned from enrich_domain result
        assert result.company_info is not None

    def test_enrich_domain_result_assigned_to_company_info(self):
        """Line 169: result.company_info = real_info."""
        e = make_enricher()
        contact = make_contact("ceo@acme.com", "acme.com")
        # All HTTP calls return 404 (no exception, just no data)
        def _return_404(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 404
            return resp
        e.session.get = _return_404
        real_info = CompanyInfo(name="Real Corp", domain="acme.com")

        with patch.object(e, "enrich_domain", return_value=real_info):
            result = e.enrich_contact(contact)

        assert result.company_info is not None
        assert result.company_info.name == "Real Corp"
