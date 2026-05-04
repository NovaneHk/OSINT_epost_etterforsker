"""
Unit tests for lead scoring functionality
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from scoring.scorer import LeadScorer, ScoreResult, ScoreComponent, PersonaMatch
from core.database import Contact, ContactStatus


class TestPersonaMatch:
    """Test PersonaMatch dataclass"""

    def test_persona_match_creation(self):
        """Test creating a persona match"""
        match = PersonaMatch(
            persona_id="technical_leaders",
            match_score=0.85,
            matched_criteria=["CTO", "Software Engineer", "tech@company.com"],
            confidence=0.9,
            reasoning="Strong technical role indicators"
        )

        assert match.persona_id == "technical_leaders"
        assert match.match_score == 0.85
        assert len(match.matched_criteria) == 3
        assert "CTO" in match.matched_criteria
        assert match.confidence == 0.9
        assert match.reasoning == "Strong technical role indicators"

    def test_persona_match_defaults(self):
        """Test persona match with default values"""
        match = PersonaMatch(
            persona_id="technical_leaders",
            match_score=0.75
        )

        assert match.persona_id == "technical_leaders"
        assert match.match_score == 0.75
        assert match.matched_criteria == []
        assert match.confidence == 0.0
        assert match.reasoning is None


class TestScoreComponent:
    """Test ScoreComponent dataclass"""

    def test_score_component_creation(self):
        """Test creating a score component"""
        component = ScoreComponent(
            name="domain_quality",
            score=0.8,
            weight=0.3,
            description="Domain reputation and authority",
            details={"domain_age": 5, "ssl_cert": True}
        )

        assert component.name == "domain_quality"
        assert component.score == 0.8
        assert component.weight == 0.3
        assert component.description == "Domain reputation and authority"
        assert component.details["domain_age"] == 5
        assert component.details["ssl_cert"] is True

    def test_score_component_weighted_score(self):
        """Test weighted score calculation"""
        component = ScoreComponent(
            name="test_component",
            score=0.6,
            weight=0.4
        )

        weighted_score = component.score * component.weight
        assert weighted_score == 0.24


class TestScoreResult:
    """Test ScoreResult dataclass"""

    def test_score_result_creation(self):
        """Test creating a score result"""
        persona_matches = [
            PersonaMatch(persona_id="technical_leaders", match_score=0.9),
            PersonaMatch(persona_id="procurement_specialists", match_score=0.3)
        ]

        components = [
            ScoreComponent(name="persona_match", score=0.9, weight=0.4),
            ScoreComponent(name="domain_quality", score=0.7, weight=0.3),
            ScoreComponent(name="role_relevance", score=0.8, weight=0.3)
        ]

        result = ScoreResult(
            contact_email="test@example.com",
            overall_score=0.82,
            confidence=0.85,
            persona_matches=persona_matches,
            best_persona="technical_leaders",
            score_components=components,
            calculation_time=1.2,
            scoring_version="1.0"
        )

        assert result.contact_email == "test@example.com"
        assert result.overall_score == 0.82
        assert result.confidence == 0.85
        assert len(result.persona_matches) == 2
        assert result.best_persona == "technical_leaders"
        assert len(result.score_components) == 3
        assert result.calculation_time == 1.2
        assert result.scoring_version == "1.0"
        assert result.timestamp is not None

    def test_score_result_defaults(self):
        """Test score result with default values"""
        result = ScoreResult(
            contact_email="test@example.com",
            overall_score=0.5
        )

        assert result.contact_email == "test@example.com"
        assert result.overall_score == 0.5
        assert result.confidence == 0.0
        assert result.persona_matches == []
        assert result.best_persona is None
        assert result.score_components == []
        assert result.calculation_time == 0.0
        assert result.scoring_version == "1.0"


class TestLeadScorer:
    """Test LeadScorer class"""

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock configuration manager"""
        config_manager = Mock()

        # Mock personas configuration
        personas_config = {
            "personas": {
                "technical_leaders": {
                    "description": "Technical decision makers",
                    "roles": ["CTO", "VP Engineering", "Tech Lead", "Software Engineer"],
                    "email_patterns": ["tech@", "engineering@", "dev@"],
                    "negative_signals": ["noreply@", "marketing@"],
                    "scoring_weight": 9,
                    "priority_level": "high"
                },
                "procurement_specialists": {
                    "description": "Procurement and purchasing professionals",
                    "roles": ["Procurement Manager", "Purchasing", "Buyer"],
                    "email_patterns": ["procurement@", "purchasing@"],
                    "negative_signals": ["noreply@"],
                    "scoring_weight": 7,
                    "priority_level": "medium"
                }
            }
        }

        # Mock rules configuration
        rules_config = {
            "processing_rules": {
                "scoring_weights": {
                    "persona_match": 0.4,
                    "domain_quality": 0.25,
                    "role_relevance": 0.20,
                    "email_validity": 0.15
                },
                "confidence_thresholds": {
                    "high": 0.8,
                    "medium": 0.6,
                    "low": 0.4
                }
            }
        }

        config_manager.load_personas.return_value = personas_config
        config_manager.load_rules.return_value = rules_config

        return config_manager

    @pytest.fixture
    def scorer(self, mock_config_manager):
        """Create a LeadScorer instance for testing"""
        return LeadScorer(config_manager=mock_config_manager)

    def test_scorer_initialization(self, scorer, mock_config_manager):
        """Test scorer initialization"""
        assert scorer.config_manager == mock_config_manager
        assert scorer.scoring_weights["persona_match"] == 0.4
        assert scorer.scoring_weights["domain_quality"] == 0.25
        assert len(scorer.personas) == 2
        assert "technical_leaders" in scorer.personas
        assert "procurement_specialists" in scorer.personas

    def test_score_contact_full(self, scorer):
        """Test full contact scoring"""
        contact = Contact(
            email="john.doe@techcorp.com",
            domain="techcorp.com",
            name="John Doe",
            role="VP Engineering",
            company="TechCorp Inc",
            sector="technology",
            confidence_score=0.9,
            status=ContactStatus.VALIDATED
        )

        result = scorer.score_contact(contact)

        assert result.contact_email == "john.doe@techcorp.com"
        assert result.overall_score > 0.0
        assert len(result.persona_matches) > 0
        assert result.best_persona is not None
        assert len(result.score_components) > 0
        assert result.confidence > 0.0
        assert result.calculation_time > 0.0

    def test_score_persona_match_strong(self, scorer):
        """Test persona matching with strong signals"""
        contact = Contact(
            email="cto@company.com",
            domain="company.com",
            name="Alice Smith",
            role="CTO",
            company="Tech Company"
        )

        persona_matches = scorer._score_persona_matches(contact)

        # Should have high match for technical_leaders
        tech_match = next((m for m in persona_matches if m.persona_id == "technical_leaders"), None)
        assert tech_match is not None
        assert tech_match.match_score > 0.7
        assert "CTO" in tech_match.matched_criteria
        assert "cto@" in [c for c in tech_match.matched_criteria if "cto@" in c.lower()]

    def test_score_persona_match_weak(self, scorer):
        """Test persona matching with weak signals"""
        contact = Contact(
            email="info@company.com",
            domain="company.com",
            name="Generic Contact",
            role="Contact",
            company="Some Company"
        )

        persona_matches = scorer._score_persona_matches(contact)

        # Should have low matches for all personas
        for match in persona_matches:
            assert match.match_score < 0.5

    def test_score_persona_match_negative_signals(self, scorer):
        """Test persona matching with negative signals"""
        contact = Contact(
            email="noreply@company.com",
            domain="company.com",
            name="No Reply",
            role="CTO",  # Would normally score high
            company="Tech Company"
        )

        persona_matches = scorer._score_persona_matches(contact)

        # Even with good role, negative email should reduce score
        tech_match = next((m for m in persona_matches if m.persona_id == "technical_leaders"), None)
        assert tech_match is not None
        # Score should be reduced due to negative signal
        assert tech_match.match_score < 0.8

    def test_score_domain_quality_business(self, scorer):
        """Test domain quality scoring for business domain"""
        contact = Contact(
            email="contact@enterprise.com",
            domain="enterprise.com"
        )

        component = scorer._score_domain_quality(contact)

        assert component.name == "domain_quality"
        assert component.score > 0.5  # Business domain should score reasonably
        assert component.weight == 0.25
        assert "domain_type" in component.details

    def test_score_domain_quality_free_provider(self, scorer):
        """Test domain quality scoring for free email provider"""
        contact = Contact(
            email="user@gmail.com",
            domain="gmail.com"
        )

        component = scorer._score_domain_quality(contact)

        assert component.name == "domain_quality"
        assert component.score < 0.8  # Free provider should score lower
        assert component.details["is_free_provider"] is True

    def test_score_role_relevance_high(self, scorer):
        """Test role relevance scoring for highly relevant role"""
        contact = Contact(
            email="test@company.com",
            role="VP Engineering",
            company="Tech Corp"
        )

        component = scorer._score_role_relevance(contact)

        assert component.name == "role_relevance"
        assert component.score > 0.7  # VP Engineering should score high
        assert component.weight == 0.20

    def test_score_role_relevance_low(self, scorer):
        """Test role relevance scoring for low relevance role"""
        contact = Contact(
            email="test@company.com",
            role="Janitor",
            company="Some Corp"
        )

        component = scorer._score_role_relevance(contact)

        assert component.name == "role_relevance"
        assert component.score < 0.3  # Janitor should score low for B2B leads

    def test_score_email_validity_valid(self, scorer):
        """Test email validity scoring for valid email"""
        contact = Contact(
            email="valid@company.com",
            confidence_score=0.9,
            status=ContactStatus.VALIDATED
        )

        component = scorer._score_email_validity(contact)

        assert component.name == "email_validity"
        assert component.score > 0.8  # High confidence + validated should score high
        assert component.weight == 0.15

    def test_score_email_validity_invalid(self, scorer):
        """Test email validity scoring for invalid email"""
        contact = Contact(
            email="bounced@company.com",
            confidence_score=0.2,
            status=ContactStatus.BOUNCED
        )

        component = scorer._score_email_validity(contact)

        assert component.name == "email_validity"
        assert component.score < 0.3  # Low confidence + bounced should score low

    def test_calculate_overall_score(self, scorer):
        """Test overall score calculation"""
        components = [
            ScoreComponent(name="persona_match", score=0.8, weight=0.4),
            ScoreComponent(name="domain_quality", score=0.7, weight=0.3),
            ScoreComponent(name="role_relevance", score=0.9, weight=0.2),
            ScoreComponent(name="email_validity", score=0.6, weight=0.1)
        ]

        overall_score = scorer._calculate_overall_score(components)

        # Expected: (0.8*0.4) + (0.7*0.3) + (0.9*0.2) + (0.6*0.1) = 0.77
        expected = 0.32 + 0.21 + 0.18 + 0.06
        assert abs(overall_score - expected) < 0.01

    def test_calculate_confidence_high(self, scorer):
        """Test confidence calculation for high-quality data"""
        contact = Contact(
            email="cto@techcorp.com",
            name="John Smith",
            role="CTO",
            company="TechCorp Inc",
            confidence_score=0.9,
            status=ContactStatus.VALIDATED
        )

        components = [
            ScoreComponent(name="persona_match", score=0.9, weight=0.4),
            ScoreComponent(name="domain_quality", score=0.8, weight=0.3),
            ScoreComponent(name="role_relevance", score=0.9, weight=0.2),
            ScoreComponent(name="email_validity", score=0.9, weight=0.1)
        ]

        confidence = scorer._calculate_confidence(contact, components)

        assert confidence > 0.8  # Should have high confidence

    def test_calculate_confidence_low(self, scorer):
        """Test confidence calculation for low-quality data"""
        contact = Contact(
            email="unknown@company.com",
            name=None,
            role=None,
            company=None,
            confidence_score=0.3,
            status=ContactStatus.UNVALIDATED
        )

        components = [
            ScoreComponent(name="persona_match", score=0.2, weight=0.4),
            ScoreComponent(name="domain_quality", score=0.5, weight=0.3),
            ScoreComponent(name="role_relevance", score=0.1, weight=0.2),
            ScoreComponent(name="email_validity", score=0.3, weight=0.1)
        ]

        confidence = scorer._calculate_confidence(contact, components)

        assert confidence < 0.5  # Should have low confidence

    def test_match_persona_criteria_role_match(self, scorer):
        """Test persona criteria matching by role"""
        contact = Contact(
            email="test@company.com",
            role="Software Engineer",
            company="Tech Corp"
        )

        persona = scorer.personas["technical_leaders"]
        matched_criteria, match_score = scorer._match_persona_criteria(contact, persona)

        assert "Software Engineer" in matched_criteria
        assert match_score > 0.5

    def test_match_persona_criteria_email_pattern(self, scorer):
        """Test persona criteria matching by email pattern"""
        contact = Contact(
            email="engineering@company.com",
            role="Manager",
            company="Tech Corp"
        )

        persona = scorer.personas["technical_leaders"]
        matched_criteria, match_score = scorer._match_persona_criteria(contact, persona)

        assert any("engineering@" in criterion for criterion in matched_criteria)
        assert match_score > 0.3

    def test_match_persona_criteria_negative_signals(self, scorer):
        """Test persona criteria matching with negative signals"""
        contact = Contact(
            email="noreply@company.com",
            role="CTO",  # Positive signal
            company="Tech Corp"
        )

        persona = scorer.personas["technical_leaders"]
        matched_criteria, match_score = scorer._match_persona_criteria(contact, persona)

        # Should have positive match for role but penalty for negative email
        assert "CTO" in matched_criteria
        assert match_score < 0.8  # Reduced due to negative signal

    def test_is_business_domain(self, scorer):
        """Test business domain detection"""
        # Business domains
        assert scorer._is_business_domain("company.com") is True
        assert scorer._is_business_domain("enterprise.co.uk") is True
        assert scorer._is_business_domain("startup.io") is True

        # Free providers
        assert scorer._is_business_domain("gmail.com") is False
        assert scorer._is_business_domain("yahoo.com") is False
        assert scorer._is_business_domain("hotmail.com") is False

    def test_get_domain_type(self, scorer):
        """Test domain type classification"""
        assert scorer._get_domain_type("company.com") == "business"
        assert scorer._get_domain_type("gmail.com") == "free_provider"
        assert scorer._get_domain_type("university.edu") == "educational"
        assert scorer._get_domain_type("government.gov") == "government"
        assert scorer._get_domain_type("nonprofit.org") == "organization"

    def test_score_contact_batch(self, scorer):
        """Test batch scoring of multiple contacts"""
        contacts = [
            Contact(email="cto@company1.com", role="CTO", company="Company 1"),
            Contact(email="user@gmail.com", role="Student", company="University"),
            Contact(email="procurement@company2.com", role="Buyer", company="Company 2")
        ]

        results = scorer.score_contacts_batch(contacts)

        assert len(results) == 3
        assert all(isinstance(result, ScoreResult) for result in results)
        assert all(result.overall_score >= 0.0 and result.overall_score <= 1.0 for result in results)

        # CTO should score higher than student
        cto_result = next(r for r in results if r.contact_email == "cto@company1.com")
        student_result = next(r for r in results if r.contact_email == "user@gmail.com")
        assert cto_result.overall_score > student_result.overall_score

    def test_get_score_explanation(self, scorer):
        """Test score explanation generation"""
        contact = Contact(
            email="cto@techcorp.com",
            role="CTO",
            company="TechCorp Inc"
        )

        result = scorer.score_contact(contact)
        explanation = scorer.get_score_explanation(result)

        assert isinstance(explanation, dict)
        assert "overall_score" in explanation
        assert "confidence" in explanation
        assert "best_persona" in explanation
        assert "components" in explanation
        assert "reasoning" in explanation
        assert isinstance(explanation["reasoning"], str)
        assert len(explanation["reasoning"]) > 0

    def test_update_scoring_weights(self, scorer):
        """Test updating scoring weights"""
        new_weights = {
            "persona_match": 0.5,
            "domain_quality": 0.3,
            "role_relevance": 0.15,
            "email_validity": 0.05
        }

        scorer.update_scoring_weights(new_weights)

        assert scorer.scoring_weights["persona_match"] == 0.5
        assert scorer.scoring_weights["domain_quality"] == 0.3
        assert scorer.scoring_weights["role_relevance"] == 0.15
        assert scorer.scoring_weights["email_validity"] == 0.05

    def test_update_scoring_weights_invalid_sum(self, scorer):
        """Test updating scoring weights with invalid sum"""
        invalid_weights = {
            "persona_match": 0.6,
            "domain_quality": 0.6,  # Total > 1.0
            "role_relevance": 0.2,
            "email_validity": 0.1
        }

        with pytest.raises(ValueError, match="must sum to 1.0"):
            scorer.update_scoring_weights(invalid_weights)

    def test_score_contact_missing_data(self, scorer):
        """Test scoring contact with missing data"""
        contact = Contact(
            email="unknown@company.com",
            domain="company.com"
            # Missing name, role, company, etc.
        )

        result = scorer.score_contact(contact)

        assert result.contact_email == "unknown@company.com"
        assert result.overall_score >= 0.0
        assert result.confidence < 0.8  # Should have lower confidence due to missing data

    def test_scoring_reproducibility(self, scorer):
        """Test that scoring is reproducible"""
        contact = Contact(
            email="test@company.com",
            role="Engineer",
            company="Test Corp"
        )

        result1 = scorer.score_contact(contact)
        result2 = scorer.score_contact(contact)

        assert result1.overall_score == result2.overall_score
        assert result1.confidence == result2.confidence
        assert result1.best_persona == result2.best_persona

    # --- _get_domain_type ---

    def test_get_domain_type_free_provider(self, scorer):
        assert scorer._get_domain_type("gmail.com") == "free_provider"
        assert scorer._get_domain_type("yahoo.com") == "free_provider"

    def test_get_domain_type_educational(self, scorer):
        assert scorer._get_domain_type("mit.edu") == "educational"

    def test_get_domain_type_government(self, scorer):
        assert scorer._get_domain_type("fda.gov") == "government"

    def test_get_domain_type_organization(self, scorer):
        assert scorer._get_domain_type("redcross.org") == "organization"

    def test_get_domain_type_business_default(self, scorer):
        assert scorer._get_domain_type("acmecorp.com") == "business"

    # --- _is_business_domain ---

    def test_is_business_domain_true(self, scorer):
        assert scorer._is_business_domain("enterprise.com") is True
        assert scorer._is_business_domain("techstartup.io") is True

    def test_is_business_domain_false_for_free_providers(self, scorer):
        assert scorer._is_business_domain("gmail.com") is False
        assert scorer._is_business_domain("outlook.com") is False

    # --- score_contacts_batch ---

    def test_score_contacts_batch_returns_all(self, scorer):
        contacts = [
            Contact(email="a@co.com", domain="co.com", role="CTO"),
            Contact(email="b@co.com", domain="co.com", role="Intern"),
        ]
        results = scorer.score_contacts_batch(contacts)
        assert len(results) == 2
        assert all(hasattr(r, "overall_score") for r in results)

    def test_score_contacts_batch_empty(self, scorer):
        results = scorer.score_contacts_batch([])
        assert results == []

    def test_score_contacts_batch_score_order(self, scorer):
        cto = Contact(email="cto@co.com", domain="co.com", role="CTO", name="Alice", company="TechCo", confidence_score=0.9, status=ContactStatus.VALIDATED)
        intern = Contact(email="intern@co.com", domain="co.com", role="Intern", confidence_score=0.1)
        results = scorer.score_contacts_batch([cto, intern])
        assert results[0].overall_score > results[1].overall_score

    # --- get_score_explanation ---

    def test_get_score_explanation_structure(self, scorer):
        result = ScoreResult(
            contact_email="x@y.com",
            overall_score=0.75,
            confidence=0.8,
            best_persona="technical_leaders",
            score_components=[
                ScoreComponent(name="persona_match", score=0.9, weight=0.4),
                ScoreComponent(name="domain_quality", score=0.7, weight=0.25),
            ],
        )
        explanation = scorer.get_score_explanation(result)
        assert "overall_score" in explanation
        assert "confidence" in explanation
        assert "best_persona" in explanation
        assert "components" in explanation
        assert "reasoning" in explanation

    def test_get_score_explanation_components_detail(self, scorer):
        result = ScoreResult(
            contact_email="x@y.com",
            overall_score=0.6,
            score_components=[
                ScoreComponent(name="role_relevance", score=0.5, weight=0.2),
            ],
        )
        explanation = scorer.get_score_explanation(result)
        comp = explanation["components"][0]
        assert comp["name"] == "role_relevance"
        assert "weighted" in comp

    def test_get_score_explanation_no_persona(self, scorer):
        result = ScoreResult(contact_email="x@y.com", overall_score=0.3)
        explanation = scorer.get_score_explanation(result)
        assert explanation["best_persona"] is None

    # --- update_scoring_weights ---

    def test_update_scoring_weights_valid(self, scorer):
        new_weights = {
            "persona_match": 0.5,
            "domain_quality": 0.2,
            "role_relevance": 0.2,
            "email_validity": 0.1,
        }
        scorer.update_scoring_weights(new_weights)
        assert scorer.scoring_weights["persona_match"] == 0.5
        assert scorer.scoring_weights["domain_quality"] == 0.2

    def test_update_scoring_weights_invalid_raises(self, scorer):
        bad = {"a": 0.6, "b": 0.6}
        with pytest.raises(ValueError):
            scorer.update_scoring_weights(bad)

    def test_update_scoring_weights_updates_default_weights(self, scorer):
        new_weights = {"persona_match": 0.4, "domain_quality": 0.3, "role_relevance": 0.2, "email_validity": 0.1}
        scorer.update_scoring_weights(new_weights)
        assert scorer.default_weights == scorer.scoring_weights

    # --- score_all_leads ---

    def test_score_all_leads_empty_db(self, scorer, mock_config_manager):
        scorer.db_manager = Mock()
        scorer.db_manager.get_all_contacts.return_value = []
        scorer.db_manager.add_contact.return_value = None

        result = scorer.score_all_leads()

        assert result["total_leads"] == 0
        assert result["high_quality_leads"] == 0
        assert result["quality_rate"] == 0

    def test_score_all_leads_with_contacts(self, scorer):
        scorer.db_manager = Mock()
        contacts = [
            Contact(email="a@co.com", domain="co.com", role="CTO", name="A", company="Co", confidence_score=0.9, status=ContactStatus.VALIDATED),
            Contact(email="b@co.com", domain="co.com", role="Janitor", confidence_score=0.1),
        ]
        scorer.db_manager.get_all_contacts.return_value = contacts
        scorer.db_manager.add_contact.return_value = None

        result = scorer.score_all_leads(min_score=50)

        assert result["total_leads"] == 2
        assert "score_distribution" in result
        assert "high" in result["score_distribution"]

    def test_score_all_leads_exception_counted(self, scorer):
        scorer.db_manager = Mock()
        bad_contact = Mock(spec=Contact)
        bad_contact.email = "bad@co.com"
        # Make score_contact raise when called with this contact
        scorer.db_manager.get_all_contacts.return_value = [bad_contact]

        with patch.object(scorer, "score_contact", side_effect=Exception("scoring error")):
            result = scorer.score_all_leads()

        # Exception shouldn't crash the run, just count the contact
        assert result["total_leads"] == 1

    # --- ScoringResult alias ---

    def test_scoring_result_alias(self):
        from scoring.scorer import ScoringResult
        r = ScoringResult(contact_email="a@b.com", overall_score=0.5)
        assert r.contact_email == "a@b.com"

    # --- ROLE_SCORES coverage ---

    def test_role_scores_ceo_max(self, scorer):
        contact = Contact(email="ceo@corp.com", domain="corp.com", role="CEO")
        comp = scorer._score_role_relevance(contact)
        assert comp.score == 1.0

    def test_role_scores_student_min(self, scorer):
        contact = Contact(email="s@uni.edu", domain="uni.edu", role="Student")
        comp = scorer._score_role_relevance(contact)
        assert comp.score <= 0.15

    def test_role_scores_procurement(self, scorer):
        # 'manager' key (0.6) is found before 'procurement' (0.75) in iteration order
        contact = Contact(email="p@corp.com", domain="corp.com", role="Procurement Manager")
        comp = scorer._score_role_relevance(contact)
        assert comp.score == 0.6

    def test_role_scores_unknown_role(self, scorer):
        contact = Contact(email="x@corp.com", domain="corp.com", role="Xyzzy Officer")
        comp = scorer._score_role_relevance(contact)
        assert comp.score == 0.25  # Default

    # --- edge cases for domain scoring ---

    def test_domain_score_educational(self, scorer):
        contact = Contact(email="prof@mit.edu", domain="mit.edu")
        comp = scorer._score_domain_quality(contact)
        assert comp.details["domain_type"] == "educational"
        assert comp.score == 0.6

    def test_domain_score_government(self, scorer):
        contact = Contact(email="agent@agency.gov", domain="agency.gov")
        comp = scorer._score_domain_quality(contact)
        assert comp.details["domain_type"] == "government"

    def test_domain_score_organization(self, scorer):
        contact = Contact(email="coord@ngo.org", domain="ngo.org")
        comp = scorer._score_domain_quality(contact)
        assert comp.details["domain_type"] == "organization"

    # --- _score_email_validity for different statuses ---

    def test_email_validity_opted_out(self, scorer):
        contact = Contact(email="x@co.com", confidence_score=0.8, status=ContactStatus.OPTED_OUT)
        comp = scorer._score_email_validity(contact)
        assert comp.score == 0.1

    def test_email_validity_invalid_status(self, scorer):
        contact = Contact(email="x@co.com", confidence_score=0.5, status=ContactStatus.INVALID)
        comp = scorer._score_email_validity(contact)
        assert comp.score == 0.0

    def test_email_validity_contacted_status(self, scorer):
        contact = Contact(email="x@co.com", confidence_score=0.8, status=ContactStatus.CONTACTED)
        comp = scorer._score_email_validity(contact)
        assert comp.score > 0.5