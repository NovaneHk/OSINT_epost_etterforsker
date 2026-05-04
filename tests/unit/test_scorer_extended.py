"""Extended tests for scoring/scorer.py — covers calculate_lead_score and related methods."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


def _make_scorer(personas=None, rules_config=None, db_emails=None):
    """Create a LeadScorer with minimal mocked dependencies."""
    from scoring.scorer import LeadScorer

    mock_config = MagicMock()
    _rules = rules_config or {}
    _personas = {"personas": personas or {}}
    mock_config.load_rules.return_value = _rules
    mock_config.load_personas.return_value = _personas

    mock_db = MagicMock()
    mock_db.get_emails.return_value = db_emails or []

    scorer = LeadScorer.__new__(LeadScorer)
    scorer.config_manager = mock_config
    scorer.db_manager = mock_db
    scorer.rules_config = _rules
    scorer.personas_config = _personas
    scorer.scoring_weights = {
        "persona_match": 0.4,
        "domain_quality": 0.25,
        "role_relevance": 0.20,
        "email_validity": 0.15,
    }
    scorer.personas = personas or {}
    scorer.default_weights = scorer.scoring_weights
    return scorer, mock_db


# ---------------------------------------------------------------------------
# calculate_lead_score
# ---------------------------------------------------------------------------
class TestCalculateLeadScore:
    def setup_method(self):
        self.scorer, self.mock_db = _make_scorer()

    def _weights(self):
        return {
            "persona_match": 0.4,
            "sector_relevance": 0.2,
            "geographic_preference": 0.15,
            "source_credibility": 0.15,
            "data_freshness": 0.1,
        }

    def test_returns_int_in_range(self):
        email_data = {"email": "cto@company.com", "role": "CTO", "confidence": 0.9, "validation_status": "valid", "mx_valid": True, "risk_score": 10}
        company_data = {"industry": "technology", "country": "US", "domain": "company.com", "credibility_score": 80}
        score = self.scorer.calculate_lead_score(email_data, company_data, self._weights())
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_low_score_for_empty_email(self):
        email_data = {"email": "", "role": "", "confidence": 0.0, "validation_status": "invalid", "mx_valid": False, "risk_score": 90}
        company_data = {}
        score = self.scorer.calculate_lead_score(email_data, company_data, self._weights())
        assert score < 20  # heavy penalty + no data → very low

    def test_penalty_for_invalid_email(self):
        email_data = {"email": "bad@bad.com", "role": "CTO", "confidence": 0.8, "validation_status": "invalid", "mx_valid": False, "risk_score": 90}
        company_data = {"credibility_score": 50}
        score = self.scorer.calculate_lead_score(email_data, company_data, self._weights())
        assert score < 50  # heavy penalty

    def test_high_score_for_clean_valid_lead(self):
        email_data = {"email": "cto@techcorp.com", "role": "CTO", "confidence": 1.0, "validation_status": "valid", "mx_valid": True, "risk_score": 0,
                      "extracted_at": datetime.now().isoformat()}
        company_data = {"industry": "technology", "country": "US", "domain": "techcorp.com", "credibility_score": 90, "source_type": "company_site"}
        score = self.scorer.calculate_lead_score(email_data, company_data, self._weights())
        assert score > 0


# ---------------------------------------------------------------------------
# _calculate_persona_score
# ---------------------------------------------------------------------------
class TestCalculatePersonaScore:
    def setup_method(self):
        personas = {
            "technical_leaders": {
                "roles": ["CTO", "VP Engineering"],
                "email_patterns": ["cto@", "vpeng@"],
                "negative_signals": ["intern"],
                "priority_level": "high",
            }
        }
        self.scorer, _ = _make_scorer(personas=personas)

    def test_matching_role_returns_nonzero(self):
        email_data = {"email": "cto@company.com", "role": "CTO", "confidence": 1.0}
        score = self.scorer._calculate_persona_score(email_data, {})
        assert score > 0

    def test_no_email_returns_zero(self):
        score = self.scorer._calculate_persona_score({"email": "", "role": "", "confidence": 0}, {})
        assert score == 0.0

    def test_negative_signal_penalizes(self):
        email_data = {"email": "intern_cto@company.com", "role": "CTO intern", "confidence": 1.0}
        score_clean = self.scorer._calculate_persona_score({"email": "cto@company.com", "role": "CTO", "confidence": 1.0}, {})
        score_penalized = self.scorer._calculate_persona_score(email_data, {})
        assert score_penalized <= score_clean

    def test_email_pattern_match(self):
        email_data = {"email": "cto@testco.com", "role": "unknown", "confidence": 1.0}
        score = self.scorer._calculate_persona_score(email_data, {})
        assert score > 0

    def test_no_personas_returns_zero(self):
        scorer, _ = _make_scorer(personas={})
        score = scorer._calculate_persona_score({"email": "a@b.com", "role": "CTO", "confidence": 1.0}, {})
        assert score == 0.0


# ---------------------------------------------------------------------------
# _calculate_sector_score
# ---------------------------------------------------------------------------
class TestCalculateSectorScore:
    def setup_method(self):
        rules = {
            "sector_definitions": {
                "tech": {
                    "keywords": ["technology", "software"],
                    "negative_keywords": ["hardware"],
                    "technology_signals": ["cloud", "kubernetes"],
                    "scoring_multiplier": 1.2,
                }
            }
        }
        self.scorer, _ = _make_scorer(rules_config=rules)

    def test_matching_industry(self):
        score = self.scorer._calculate_sector_score({"industry": "technology", "technologies": []})
        assert score > 0

    def test_no_industry_neutral(self):
        score = self.scorer._calculate_sector_score({})
        assert score == 0.5

    def test_negative_industry_reduces_score(self):
        pos = self.scorer._calculate_sector_score({"industry": "technology", "technologies": []})
        neg = self.scorer._calculate_sector_score({"industry": "hardware", "technologies": []})
        assert neg <= pos

    def test_technology_signals_boost(self):
        base = self.scorer._calculate_sector_score({"industry": "technology", "technologies": []})
        boosted = self.scorer._calculate_sector_score({"industry": "technology", "technologies": ["cloud computing"]})
        assert boosted >= base

    def test_empty_rules_sector(self):
        scorer, _ = _make_scorer(rules_config={})
        score = scorer._calculate_sector_score({"industry": "finance", "technologies": []})
        assert score == 0.0  # no sector defs


# ---------------------------------------------------------------------------
# _calculate_geographic_score
# ---------------------------------------------------------------------------
class TestCalculateGeographicScore:
    def setup_method(self):
        rules = {
            "geographic_targeting": {
                "nordic": {
                    "countries": ["NO", "SE", "DK"],
                    "tld_preferences": [".no", ".se"],
                    "scoring_boost": 20,
                }
            }
        }
        self.scorer, _ = _make_scorer(rules_config=rules)

    def test_matching_country(self):
        score = self.scorer._calculate_geographic_score({"country": "NO", "domain": "company.com"})
        assert score > 0.5

    def test_matching_tld(self):
        score = self.scorer._calculate_geographic_score({"country": "", "domain": "company.no"})
        assert score > 0

    def test_unknown_country_is_neutral(self):
        score = self.scorer._calculate_geographic_score({})
        assert score == 0.5

    def test_no_geo_rules(self):
        scorer, _ = _make_scorer(rules_config={})
        score = scorer._calculate_geographic_score({"country": "US", "domain": "company.com"})
        assert score == 0.0


# ---------------------------------------------------------------------------
# _calculate_source_credibility_score
# ---------------------------------------------------------------------------
class TestCalculateSourceCredibilityScore:
    def setup_method(self):
        self.scorer, _ = _make_scorer()

    def test_company_site_has_multiplier(self):
        email_data = {"source_type": "company_site"}
        company_data = {"credibility_score": 50}
        score = self.scorer._calculate_source_credibility_score(email_data, company_data)
        assert score > 0.5

    def test_unknown_source_penalized(self):
        email_data = {"source_type": "unknown"}
        company_data = {"credibility_score": 50}
        score = self.scorer._calculate_source_credibility_score(email_data, company_data)
        assert score < 0.5

    def test_event_source(self):
        email_data = {"source_type": "event"}
        company_data = {"credibility_score": 60}
        score = self.scorer._calculate_source_credibility_score(email_data, company_data)
        assert score > 0

    def test_zero_credibility(self):
        email_data = {"source_type": "directory"}
        company_data = {"credibility_score": 0}
        score = self.scorer._calculate_source_credibility_score(email_data, company_data)
        assert score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _calculate_freshness_score
# ---------------------------------------------------------------------------
class TestCalculateFreshnessScore:
    def setup_method(self):
        self.scorer, _ = _make_scorer()

    def test_no_date_is_neutral(self):
        assert self.scorer._calculate_freshness_score({}) == 0.5

    def test_fresh_data_score_1(self):
        recent = (datetime.now() - timedelta(days=3)).isoformat()
        assert self.scorer._calculate_freshness_score({"extracted_at": recent}) == 1.0

    def test_month_old_score_0_8(self):
        old = (datetime.now() - timedelta(days=20)).isoformat()
        assert self.scorer._calculate_freshness_score({"extracted_at": old}) == 0.8

    def test_3_months_old_score_0_6(self):
        old = (datetime.now() - timedelta(days=60)).isoformat()
        assert self.scorer._calculate_freshness_score({"extracted_at": old}) == 0.6

    def test_6_months_old_score_0_4(self):
        old = (datetime.now() - timedelta(days=120)).isoformat()
        assert self.scorer._calculate_freshness_score({"extracted_at": old}) == 0.4

    def test_very_old_score_0_2(self):
        old = (datetime.now() - timedelta(days=200)).isoformat()
        assert self.scorer._calculate_freshness_score({"extracted_at": old}) == 0.2

    def test_invalid_date_returns_0_5(self):
        assert self.scorer._calculate_freshness_score({"extracted_at": "not-a-date"}) == 0.5


# ---------------------------------------------------------------------------
# _calculate_validation_penalty
# ---------------------------------------------------------------------------
class TestCalculateValidationPenalty:
    def setup_method(self):
        self.scorer, _ = _make_scorer()

    def test_valid_no_penalty(self):
        penalty = self.scorer._calculate_validation_penalty({"validation_status": "valid", "risk_score": 0, "mx_valid": True})
        assert penalty == 0.0

    def test_invalid_high_penalty(self):
        penalty = self.scorer._calculate_validation_penalty({"validation_status": "invalid", "risk_score": 0, "mx_valid": True})
        assert penalty >= 0.8

    def test_risky_medium_penalty(self):
        penalty = self.scorer._calculate_validation_penalty({"validation_status": "risky", "risk_score": 0, "mx_valid": True})
        assert 0.2 <= penalty <= 0.6

    def test_no_mx_adds_penalty(self):
        clean = self.scorer._calculate_validation_penalty({"validation_status": "valid", "risk_score": 0, "mx_valid": True})
        no_mx = self.scorer._calculate_validation_penalty({"validation_status": "valid", "risk_score": 0, "mx_valid": False})
        assert no_mx > clean

    def test_penalty_capped_at_1(self):
        penalty = self.scorer._calculate_validation_penalty({"validation_status": "invalid", "risk_score": 100, "mx_valid": False})
        assert penalty <= 1.0

    def test_unknown_status_light_penalty(self):
        penalty = self.scorer._calculate_validation_penalty({"validation_status": "unknown", "risk_score": 0, "mx_valid": True})
        assert 0 < penalty < 0.5


# ---------------------------------------------------------------------------
# _is_old_data
# ---------------------------------------------------------------------------
class TestIsOldData:
    def setup_method(self):
        self.scorer, _ = _make_scorer()

    def test_none_is_old(self):
        assert self.scorer._is_old_data(None) is True

    def test_fresh_is_not_old(self):
        recent = datetime.now().isoformat()
        assert self.scorer._is_old_data(recent) is False

    def test_91_days_is_old(self):
        old = (datetime.now() - timedelta(days=91)).isoformat()
        assert self.scorer._is_old_data(old) is True

    def test_invalid_string_is_old(self):
        assert self.scorer._is_old_data("not-a-date") is True

    def test_datetime_object_not_old(self):
        fresh = datetime.now()
        assert self.scorer._is_old_data(fresh) is False


# ---------------------------------------------------------------------------
# get_scoring_insights
# ---------------------------------------------------------------------------
class TestGetScoringInsights:
    def test_empty_database(self):
        scorer, _ = _make_scorer(db_emails=[])
        result = scorer.get_scoring_insights()
        assert result["total_leads"] == 0
        assert result["quality_rate"] == 0

    def test_with_leads(self):
        emails = [
            {"final_score": 80, "role": "CTO", "source_type": "directory", "domain": "company.com"},
            {"final_score": 90, "role": "CTO", "source_type": "directory", "domain": "acme.com"},
            {"final_score": 20, "role": "Intern", "source_type": "unknown", "domain": "gmail.com"},
        ]
        scorer, _ = _make_scorer(db_emails=emails)
        result = scorer.get_scoring_insights(min_score=70)
        assert result["total_leads"] == 3
        assert result["high_quality_leads"] == 2
        assert "top_roles" in result
        assert "recommendations" in result


# ---------------------------------------------------------------------------
# _generate_recommendations
# ---------------------------------------------------------------------------
class TestGenerateRecommendations:
    def setup_method(self):
        self.scorer, _ = _make_scorer()

    def test_empty_returns_message(self):
        result = self.scorer._generate_recommendations([], [])
        assert len(result) == 1
        assert "No leads" in result[0]

    def test_low_quality_rate_recommendation(self):
        all_emails = [{"final_score": 10, "validation_status": "invalid", "source_type": "a"} for _ in range(10)]
        high = []
        result = self.scorer._generate_recommendations(all_emails, high)
        assert any("quality rate" in r.lower() or "low" in r.lower() for r in result)

    def test_high_invalid_rate_recommendation(self):
        all_emails = [{"final_score": 80, "validation_status": "invalid", "source_type": "x"} for _ in range(5)]
        all_emails += [{"final_score": 80, "validation_status": "valid", "source_type": "x"} for _ in range(5)]
        high = [e for e in all_emails if e["final_score"] >= 70]
        result = self.scorer._generate_recommendations(all_emails, high)
        assert any("invalid" in r.lower() for r in result)

    def test_good_quality_positive_message(self):
        all_emails = [{"final_score": 90, "validation_status": "valid", "source_type": "company_site",
                       "extracted_at": datetime.now().isoformat()} for _ in range(5)]
        high = all_emails
        result = self.scorer._generate_recommendations(all_emails, high)
        # Should have at most a positive message (no critical warnings)
        # At least one recommendation returned
        assert len(result) > 0
