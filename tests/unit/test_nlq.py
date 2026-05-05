"""
Unit tests for NLQ parser — role search, industry search, company extraction, ranking.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestNLQParser:
    """Tests for the _parse_nlq function."""

    def test_parse_role_ceo(self):
        from backend.api.nlq import _parse_nlq
        result = _parse_nlq("Find CEO in Oslo")
        assert result["role"] == "ceo"

    def test_parse_role_engineer(self):
        from backend.api.nlq import _parse_nlq
        result = _parse_nlq("Software engineer at Google")
        assert result["role"] == "engineer"

    def test_parse_industry_tech(self):
        from backend.api.nlq import _parse_nlq
        result = _parse_nlq("tech company leaders")
        assert result["industry"] == "tech"

    def test_parse_industry_fintech(self):
        from backend.api.nlq import _parse_nlq
        result = _parse_nlq("fintech startup founders")
        assert result["industry"] == "fintech"

    def test_parse_location_oslo(self):
        from backend.api.nlq import _parse_nlq
        result = _parse_nlq("developers in Oslo with experience")
        assert result["location"] == "Oslo"

    def test_parse_location_from(self):
        from backend.api.nlq import _parse_nlq
        result = _parse_nlq("people from Bergen")
        assert result["location"] == "Bergen"

    def test_parse_company_at(self):
        from backend.api.nlq import _parse_nlq
        result = _parse_nlq("Find CTO at Acme Corp")
        assert result["company"] is not None
        assert "Acme" in result["company"]

    def test_parse_company_hos(self):
        from backend.api.nlq import _parse_nlq
        result = _parse_nlq("ansatt hos Equinor")
        assert result["company"] is not None
        assert "Equinor" in result["company"]

    def test_parse_domain_extraction(self):
        from backend.api.nlq import _parse_nlq
        result = _parse_nlq("emails from example.com")
        assert result["domain"] == "example.com"

    def test_parse_empty_query(self):
        from backend.api.nlq import _parse_nlq
        result = _parse_nlq("   ")
        assert result["role"] is None
        assert result["industry"] is None

    def test_parse_q_preserved(self):
        from backend.api.nlq import _parse_nlq
        query = "CEO in Oslo from tech company"
        result = _parse_nlq(query)
        assert result["q"] == query


class TestNLQLeadQuery:
    """Tests for _build_lead_query function."""

    def test_build_empty_filters(self):
        from backend.api.nlq import _build_lead_query
        where, params = _build_lead_query({"q": None, "role": None, "industry": None, "location": None, "domain": None, "company": None})
        assert where == ""
        assert params == []

    def test_build_with_role(self):
        from backend.api.nlq import _build_lead_query
        where, params = _build_lead_query({"q": None, "role": "ceo", "industry": None, "location": None, "domain": None, "company": None})
        assert "job_title" in where
        assert "%ceo%" in params

    def test_build_with_company(self):
        from backend.api.nlq import _build_lead_query
        where, params = _build_lead_query({"q": None, "role": None, "industry": None, "location": None, "domain": None, "company": "Google"})
        assert "company" in where.lower()
        assert "%google%" in params

    def test_build_with_multiple_filters(self):
        from backend.api.nlq import _build_lead_query
        where, params = _build_lead_query({"q": "test", "role": "ceo", "industry": "tech", "location": "Oslo", "domain": None, "company": None})
        # Should have WHERE with AND conditions
        assert "WHERE" in where
        assert len(params) >= 3
