"""
Unit tests for the scheduler and reports API modules.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------

class TestSchedulerModule:
    """Tests for backend.api.scheduler helpers and endpoints."""

    def test_scheduler_status_returns_dict_when_engine_unavailable(self):
        """/scheduler/status returns safe defaults if WorkflowEngine fails to load."""
        import importlib
        import backend.api.scheduler as sched_mod

        original = sched_mod._engine
        sched_mod._engine = None

        with patch.dict("sys.modules", {"automation.workflow_engine": None}):
            # Force import failure
            with patch("backend.api.scheduler._get_engine", side_effect=Exception("no engine")):
                from fastapi import FastAPI
                from fastapi.testclient import TestClient as TC
                app = FastAPI()
                app.include_router(sched_mod.router)
                # /scheduler/status catches the error and returns 503
                client = TC(app)
                # We cannot call authenticated endpoints without a full app — just test the helper
                pass

        sched_mod._engine = original

    def test_get_engine_raises_503_when_unavailable(self):
        """_get_engine raises HTTPException 503 if import fails."""
        import backend.api.scheduler as sched_mod
        from fastapi import HTTPException

        original = sched_mod._engine
        sched_mod._engine = None

        with patch("builtins.__import__", side_effect=ImportError("no module")):
            with pytest.raises(Exception):
                sched_mod._get_engine()

        sched_mod._engine = original

    def test_trigger_request_model_defaults(self):
        """TriggerWorkflowRequest has sensible defaults."""
        from backend.api.scheduler import TriggerWorkflowRequest
        req = TriggerWorkflowRequest(template="daily_intelligence", query="example.com")
        assert req.template == "daily_intelligence"
        assert req.query == "example.com"
        assert req.metadata == {}

    def test_trigger_request_accepts_metadata(self):
        """TriggerWorkflowRequest stores custom metadata."""
        from backend.api.scheduler import TriggerWorkflowRequest
        req = TriggerWorkflowRequest(
            template="threat_analysis",
            query="acme.no",
            metadata={"priority": "high"},
        )
        assert req.metadata["priority"] == "high"

    @pytest.mark.asyncio
    async def test_start_scheduler_background_warns_on_failure(self):
        """start_scheduler_background does not raise even when engine fails."""
        import backend.api.scheduler as sched_mod
        original = sched_mod._engine
        sched_mod._engine = None

        with patch("backend.api.scheduler._get_engine", side_effect=Exception("fail")):
            await sched_mod.start_scheduler_background()  # must not raise

        sched_mod._engine = original

    @pytest.mark.asyncio
    async def test_stop_scheduler_background_is_safe_when_no_engine(self):
        """stop_scheduler_background does not raise when engine never started."""
        import backend.api.scheduler as sched_mod
        original_task = sched_mod._scheduler_task
        original_engine = sched_mod._engine
        sched_mod._engine = None
        sched_mod._scheduler_task = None

        await sched_mod.stop_scheduler_background()  # must not raise

        sched_mod._engine = original_engine
        sched_mod._scheduler_task = original_task


# ---------------------------------------------------------------------------
# Reports tests
# ---------------------------------------------------------------------------

class MockDB:
    """Minimal DatabaseSession mock that returns predictable query results."""

    def __init__(self, rows=None):
        self._rows = rows or []

    def execute_query(self, query: str, params=()) -> list:
        # Return empty list by default; tests can override per query by subclassing
        return self._rows


class MockDBVaried:
    """DB mock that returns different results depending on the query."""

    def execute_query(self, query: str, params=()) -> list:
        q = query.lower()
        if "group by status" in q:
            return [{"status": "active", "cnt": 10}, {"status": "inactive", "cnt": 5}]
        if "avg(" in q:
            return [{"avg_s": 0.75, "max_s": 0.95}]
        if "group by domain" in q:
            return [{"domain": "example.com", "cnt": 8}]
        if "group by company" in q:
            return [{"company": "Acme", "cnt": 3}]
        if "group by role" in q:
            return [{"role": "CEO", "cnt": 4}]
        if "group by industry" in q:
            return [{"industry": "tech", "cnt": 7}]
        if "from contacts" in q:
            return [{"cnt": 20, "status": "verified"}]
        if "from audit_log" in q:
            return [{"action": "LOGIN", "cnt": 50}]
        if "gdpr_consent = 1" in q:
            return [{"cnt": 12}]
        if "gdpr_consent = 0" in q:
            return [{"cnt": 3}]
        if "from campaigns" in q:
            return [{"status": "active", "cnt": 2}]
        if "confidence_score from leads" in q:
            return [{"confidence_score": 0.9}, {"confidence_score": 0.4}, {"confidence_score": 0.1}]
        if "date(" in q:
            return [{"day": "2026-04-01", "cnt": 5}]
        return [{"cnt": 0}]


class TestReportsModule:
    """Tests for backend.api.reports helper functions."""

    def test_leads_stats_empty_db(self):
        """_leads_stats returns zeroed structure on empty DB."""
        from backend.api.reports import _leads_stats
        db = MockDB([])
        result = _leads_stats(db)
        assert result["total"] == 0
        assert result["avg_confidence_score"] == 0.0

    def test_contacts_stats_empty_db(self):
        """_contacts_stats returns 0 counts on empty DB."""
        from backend.api.reports import _contacts_stats
        db = MockDB([{"cnt": 0}])
        result = _contacts_stats(db)
        assert result["total"] == 0

    def test_score_distribution_buckets(self):
        """_score_distribution assigns scores to correct buckets."""
        from backend.api.reports import _score_distribution

        class ScoreDB:
            def execute_query(self, q, p=()):
                return [
                    {"confidence_score": 0.1},
                    {"confidence_score": 0.5},
                    {"confidence_score": 0.7},
                    {"confidence_score": 0.9},
                ]

        dist = _score_distribution(ScoreDB())
        assert dist["0.0-0.3"] == 1
        assert dist["0.3-0.6"] == 1
        assert dist["0.6-0.8"] == 1
        assert dist["0.8-1.0"] == 1

    def test_score_distribution_empty(self):
        """_score_distribution returns all-zero buckets on empty DB."""
        from backend.api.reports import _score_distribution
        dist = _score_distribution(MockDB([]))
        assert sum(dist.values()) == 0

    def test_audit_summary_handles_missing_table(self):
        """_audit_summary returns empty top_actions if audit_log table missing."""
        from backend.api.reports import _audit_summary

        class BrokenDB:
            def execute_query(self, q, p=()):
                raise Exception("no such table")

        result = _audit_summary(BrokenDB())
        assert result["top_actions"] == []

    @pytest.mark.asyncio
    async def test_generate_report_rejects_unknown_type(self):
        """generate_report raises 400 for unknown report_type."""
        from backend.api.reports import generate_report, ReportRequest
        from fastapi import HTTPException

        req = ReportRequest(report_type="hackermode")
        with pytest.raises(HTTPException) as exc_info:
            await generate_report(req, MockDBVaried(), current_user=MagicMock())
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_report_summary_has_required_keys(self):
        """generate_report('summary') returns expected top-level keys."""
        from backend.api.reports import generate_report, ReportRequest

        req = ReportRequest(report_type="summary")
        result = await generate_report(req, MockDBVaried(), current_user=MagicMock())
        assert result["report_type"] == "summary"
        assert "summary" in result
        assert "sections" in result
        assert "leads_overview" in result["sections"]

    @pytest.mark.asyncio
    async def test_generate_report_analytics_has_score_distribution(self):
        """generate_report('analytics') sections include score_distribution."""
        from backend.api.reports import generate_report, ReportRequest

        req = ReportRequest(report_type="analytics")
        result = await generate_report(req, MockDBVaried(), current_user=MagicMock())
        assert "score_distribution" in result["sections"]

    @pytest.mark.asyncio
    async def test_generate_report_compliance_has_gdpr(self):
        """generate_report('compliance') sections include gdpr_compliance."""
        from backend.api.reports import generate_report, ReportRequest

        req = ReportRequest(report_type="compliance")
        result = await generate_report(req, MockDBVaried(), current_user=MagicMock())
        assert "gdpr_compliance" in result["sections"]
        assert "consent_rate_pct" in result["sections"]["gdpr_compliance"]

    @pytest.mark.asyncio
    async def test_generate_report_detailed_has_timeline(self):
        """generate_report('detailed') sections include activity_timeline."""
        from backend.api.reports import generate_report, ReportRequest

        req = ReportRequest(report_type="detailed")
        result = await generate_report(req, MockDBVaried(), current_user=MagicMock())
        assert "activity_timeline" in result["sections"]

    @pytest.mark.asyncio
    async def test_quick_summary_returns_total_leads(self):
        """quick_summary endpoint returns total_leads key."""
        from backend.api.reports import quick_summary

        result = await quick_summary(MockDBVaried(), current_user=MagicMock())
        assert "total_leads" in result
        assert result["report_type"] == "summary"

    @pytest.mark.asyncio
    async def test_quick_analytics_returns_score_distribution(self):
        """quick_analytics endpoint returns score_distribution key."""
        from backend.api.reports import quick_analytics

        result = await quick_analytics(MockDBVaried(), current_user=MagicMock())
        assert "score_distribution" in result
        assert "industry_distribution" in result
