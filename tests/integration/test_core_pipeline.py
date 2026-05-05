"""
Integration tests for the core data pipeline:
  EmailMatch → to_contact() → add_contact() → get_contact() → score_contact()
"""

import pytest
from extract.email_extractor import EmailMatch
from core.database import Contact, ContactStatus, DatabaseManager
from scoring.scorer import LeadScorer
from unittest.mock import MagicMock, patch


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_config_manager():
    cm = MagicMock()
    cm.load_rules.return_value = {
        'processing_rules': {
            'scoring_weights': {
                'persona_match': 0.4,
                'domain_quality': 0.25,
                'role_relevance': 0.20,
                'email_validity': 0.15,
            }
        }
    }
    cm.load_personas.return_value = {'personas': {}}
    return cm


@pytest.fixture
def in_memory_db(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    return db


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestEmailMatchToContact:
    def test_to_contact_basic_fields(self):
        match = EmailMatch(
            email="cto@example.com",
            domain="example.com",
            local_part="cto",
            role="cto",
            confidence=0.9,
        )
        contact = match.to_contact(source_url="https://example.com", company="Example Ltd")

        assert contact.email == "cto@example.com"
        assert contact.domain == "example.com"
        assert contact.role == "cto"
        assert contact.company == "Example Ltd"
        assert contact.confidence_score == 0.9
        assert contact.source == "crawler"
        assert contact.source_url == "https://example.com"
        assert contact.status == ContactStatus.UNVALIDATED

    def test_to_contact_no_optional_args(self):
        match = EmailMatch(
            email="info@corp.no",
            domain="corp.no",
            local_part="info",
        )
        contact = match.to_contact()
        assert contact.email == "info@corp.no"
        assert contact.company is None
        assert contact.source_url is None


class TestContactRoundTrip:
    def test_add_and_get_contact(self, in_memory_db):
        contact = Contact(
            email="test@roundtrip.com",
            domain="roundtrip.com",
            role="engineer",
            confidence_score=0.8,
        )
        in_memory_db.add_contact(contact)
        fetched = in_memory_db.get_contact("test@roundtrip.com")

        assert fetched is not None
        assert fetched.email == "test@roundtrip.com"
        assert fetched.role == "engineer"
        assert abs(fetched.confidence_score - 0.8) < 0.01

    def test_get_all_contacts_empty(self, in_memory_db):
        contacts = in_memory_db.get_all_contacts()
        assert isinstance(contacts, list)
        assert len(contacts) == 0

    def test_get_all_contacts_returns_stored(self, in_memory_db):
        for i in range(3):
            in_memory_db.add_contact(Contact(
                email=f"user{i}@corp.com",
                domain="corp.com",
                role="manager",
            ))
        contacts = in_memory_db.get_all_contacts()
        assert len(contacts) == 3


class TestScoreContact:
    def test_score_contact_returns_score_result(self, mock_config_manager, in_memory_db):
        with patch('scoring.scorer.DatabaseManager', return_value=in_memory_db):
            scorer = LeadScorer(mock_config_manager)

        contact = Contact(
            email="cto@startup.io",
            domain="startup.io",
            role="cto",
            confidence_score=0.85,
        )
        result = scorer.score_contact(contact)

        assert result.contact_email == "cto@startup.io"
        assert 0.0 <= result.overall_score <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.score_components, list)

    def test_free_email_scores_lower(self, mock_config_manager, in_memory_db):
        with patch('scoring.scorer.DatabaseManager', return_value=in_memory_db):
            scorer = LeadScorer(mock_config_manager)

        business = Contact(email="vp@corp.com", domain="corp.com", role="vp")
        free_email = Contact(email="someone@gmail.com", domain="gmail.com", role="vp")

        r_biz = scorer.score_contact(business)
        r_free = scorer.score_contact(free_email)

        assert r_biz.domain_score > r_free.domain_score


class TestFullPipeline:
    def test_extract_to_score_pipeline(self, mock_config_manager, in_memory_db):
        """EmailMatch → to_contact() → add_contact() → score_contact()"""
        match = EmailMatch(
            email="procurement@supplierco.no",
            domain="supplierco.no",
            local_part="procurement",
            role="procurement",
            confidence=0.75,
        )
        contact = match.to_contact(source_url="https://supplierco.no", company="SupplierCo")
        in_memory_db.add_contact(contact)

        fetched = in_memory_db.get_contact("procurement@supplierco.no")
        assert fetched is not None

        with patch('scoring.scorer.DatabaseManager', return_value=in_memory_db):
            scorer = LeadScorer(mock_config_manager)

        result = scorer.score_contact(fetched)
        assert result.overall_score > 0

    def test_score_all_leads_uses_contacts_table(self, mock_config_manager, in_memory_db):
        """score_all_leads() must iterate the contacts table, not legacy emails table."""
        for i in range(5):
            in_memory_db.add_contact(Contact(
                email=f"lead{i}@b2b.com",
                domain="b2b.com",
                role="director",
                confidence_score=0.7,
            ))

        with patch('scoring.scorer.DatabaseManager', return_value=in_memory_db):
            scorer = LeadScorer(mock_config_manager)

        stats = scorer.score_all_leads(min_score=50)

        assert stats['total_leads'] == 5
        assert 'high_quality_leads' in stats
        assert 'score_distribution' in stats
        assert 'quality_rate' in stats
