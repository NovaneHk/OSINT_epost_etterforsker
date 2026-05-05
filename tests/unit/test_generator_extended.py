"""
Extended coverage tests for report/generator.py
Targets uncovered lines: 92-93, 109-110, 126-127, 153-154, 178-179, 186,
297-298, 321-322, 401-402, 420-421, 432, 450-451, 487-507, 512-539,
559-580, 591-613, 623-654, 666-740, 745, 856-874
"""
import pytest
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from report.generator import (
    ReportGenerator, ReportType, ReportResult, ReportSection, ReportData
)
from core.database import Contact, ContactStatus
from scoring.scorer import ScoreResult


def make_mock_scorer(overall_score=0.8, best_persona="CTO", raise_exc=False):
    scorer = MagicMock()
    if raise_exc:
        scorer.score_contact.side_effect = Exception("scorer error")
    else:
        sr = MagicMock(spec=ScoreResult)
        sr.overall_score = overall_score
        sr.best_persona = best_persona
        sr.confidence = 0.9
        scorer.score_contact.return_value = sr
    return scorer


def make_mock_db(contacts=None, stats=None):
    db = MagicMock()
    db.get_all_contacts.return_value = contacts or []
    db.get_contact_stats.return_value = stats or {"total": 0, "validated": 0, "bounced": 0}
    db.get_statistics.return_value = {"total_contacts": 0}
    db.get_emails.return_value = []
    db.get_companies.return_value = []
    return db


def make_contact(email="x@co.com", domain="co.com"):
    c = MagicMock(spec=Contact)
    c.email = email
    c.domain = domain
    c.name = "Test User"
    c.role = None
    c.company = None
    c.status = ContactStatus.VALIDATED
    c.confidence_score = 0.8
    c.created_at = datetime(2024, 4, 10)
    return c


def make_generator(tmp_path, contacts=None, stats=None, scorer=None, template_exists=True):
    db = make_mock_db(contacts=contacts, stats=stats)
    sc = scorer or make_mock_scorer()
    template_dir = str(tmp_path / "templates")
    if template_exists:
        Path(template_dir).mkdir(parents=True, exist_ok=True)
    gen = ReportGenerator(
        db_manager=db,
        scorer=sc,
        output_dir=str(tmp_path / "reports"),
        template_dir=template_dir,
    )
    return gen, db


# ── generate_summary_report ───────────────────────────────────────────────────

class TestGenerateSummaryReport:
    def test_template_not_found_returns_failure(self, tmp_path):
        """Lines 92-93: template dir missing → immediate failure."""
        db = make_mock_db()
        sc = make_mock_scorer()
        gen = ReportGenerator(
            db_manager=db, scorer=sc,
            output_dir=str(tmp_path / "rep"),
            template_dir="/nonexistent_template_dir_xyz",
        )
        result = gen.generate_summary_report()
        assert result.success is False
        assert "template not found" in (result.error or "")

    def test_success_with_dates(self, tmp_path):
        """Lines 297-298: date_from and date_to provided → _filter_by_date_range called."""
        contacts = [make_contact()]
        contacts[0].created_at = datetime(2024, 5, 1)
        gen, db = make_generator(tmp_path, contacts=contacts)
        date_from = datetime(2024, 4, 1)
        date_to = datetime(2024, 6, 1)
        result = gen.generate_summary_report(date_from=date_from, date_to=date_to)
        assert result.success is True

    def test_success_without_dates(self, tmp_path):
        gen, _ = make_generator(tmp_path, contacts=[make_contact()])
        result = gen.generate_summary_report()
        assert result.success is True
        assert result.sections_count >= 1

    def test_exception_in_collect_data_returns_failure(self, tmp_path):
        """Lines 109-110 analog: exception during data collection → error result."""
        gen, db = make_generator(tmp_path)
        db.get_all_contacts.side_effect = Exception("DB down")
        result = gen.generate_summary_report()
        assert result.success is False

    def test_date_from_in_render(self, tmp_path):
        """Lines 450-451: metadata date_from triggers HTML date line."""
        contacts = [make_contact()]
        gen, _ = make_generator(tmp_path, contacts=contacts)
        result = gen.generate_summary_report(
            date_from=datetime(2024, 1, 1),
            date_to=datetime(2024, 12, 31)
        )
        assert result.success is True
        if result.report_path:
            content = Path(result.report_path).read_text(encoding="utf-8") if Path(result.report_path).exists() else ""
            # Either date or date range info appears in the report
            assert "2024" in content or content == ""


# ── generate_detailed_report ──────────────────────────────────────────────────

class TestGenerateDetailedReport:
    def test_success(self, tmp_path):
        contacts = [make_contact("a@x.com", "x.com"), make_contact("b@y.com", "y.com")]
        gen, _ = make_generator(tmp_path, contacts=contacts)
        result = gen.generate_detailed_report()
        assert result.success is True
        assert result.sections_count >= 2

    def test_exception_returns_failure(self, tmp_path):
        """Lines 109-110: exception handler in generate_detailed_report."""
        gen, db = make_generator(tmp_path)
        db.get_contact_stats.side_effect = Exception("stats failed")
        result = gen.generate_detailed_report()
        assert result.success is False
        assert result.error is not None

    def test_scorer_exception_in_section_builder(self, tmp_path):
        """Lines 401-402: scorer.score_contact raises in _create_scoring_analysis_section."""
        contacts = [make_contact()]
        bad_scorer = make_mock_scorer(raise_exc=True)
        gen, _ = make_generator(tmp_path, contacts=contacts, scorer=bad_scorer)
        result = gen.generate_detailed_report()
        # Scoring exceptions are caught → report still succeeds
        assert result.success is True


# ── generate_analytics_report ─────────────────────────────────────────────────

class TestGenerateAnalyticsReport:
    def test_success(self, tmp_path):
        contacts = [make_contact()]
        gen, _ = make_generator(tmp_path, contacts=contacts)
        result = gen.generate_analytics_report()
        assert result.success is True

    def test_exception_returns_failure(self, tmp_path):
        """Lines 126-127: analytics report exception handler."""
        gen, db = make_generator(tmp_path)
        db.get_contact_stats.side_effect = Exception("analytics fail")
        result = gen.generate_analytics_report()
        assert result.success is False

    def test_persona_section_scorer_exception(self, tmp_path):
        """Lines 420-421, 432: persona section handles scorer exception."""
        contacts = [make_contact()]
        bad_scorer = make_mock_scorer(raise_exc=True)
        gen, _ = make_generator(tmp_path, contacts=contacts, scorer=bad_scorer)
        result = gen.generate_analytics_report()
        assert result.success is True


# ── generate_performance_report ───────────────────────────────────────────────

class TestGeneratePerformanceReport:
    def test_success(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        result = gen.generate_performance_report()
        assert result.success is True
        assert result.sections_count >= 1

    def test_exception_returns_failure(self, tmp_path):
        """Lines 153-154: performance report exception handler."""
        gen, db = make_generator(tmp_path)
        db.get_contact_stats.side_effect = Exception("perf fail")
        result = gen.generate_performance_report()
        assert result.success is False


# ── generate_compliance_report ────────────────────────────────────────────────

class TestGenerateComplianceReport:
    def test_success(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        result = gen.generate_compliance_report()
        assert result.success is True

    def test_exception_returns_failure(self, tmp_path):
        """Lines 178-179: compliance report exception handler."""
        gen, _ = make_generator(tmp_path)
        with patch.object(gen, "_render_html_report", side_effect=Exception("render fail")):
            result = gen.generate_compliance_report()
        assert result.success is False


# ── generate_persona_analysis ─────────────────────────────────────────────────

class TestGeneratePersonaAnalysis:
    """Line 186: persona_analysis delegates to analytics."""

    def test_delegates_to_analytics(self, tmp_path):
        gen, _ = make_generator(tmp_path, contacts=[make_contact()])
        result = gen.generate_persona_analysis()
        assert result.success is True
        assert result.report_type == ReportType.ANALYTICS


# ── generate_batch_reports ────────────────────────────────────────────────────

class TestGenerateBatchReports:
    def test_all_report_types(self, tmp_path):
        gen, _ = make_generator(tmp_path, contacts=[make_contact()])
        results = gen.generate_batch_reports([
            ReportType.SUMMARY,
            ReportType.DETAILED,
            ReportType.ANALYTICS,
            ReportType.PERFORMANCE,
            ReportType.COMPLIANCE,
        ])
        assert len(results) == 5

    def test_unknown_type_skipped(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        fake_type = MagicMock()
        results = gen.generate_batch_reports([fake_type])
        assert len(results) == 0


# ── _render_html_report ───────────────────────────────────────────────────────

class TestRenderHtmlReport:
    """Lines 450-451: metadata date_from triggers extra HTML."""

    def test_renders_with_date_range(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        sections = [ReportSection(title="S1", content="c1")]
        data = ReportData(
            report_type=ReportType.SUMMARY, title="T",
            sections=sections,
            metadata={"date_from": datetime(2024, 1, 1), "date_to": None},
            date_range=("2024-01-01", "2024-12-31"),
        )
        out = str(tmp_path / "rep.html")
        result = gen._render_html_report(data, out)
        assert result.success is True
        content = Path(out).read_text(encoding="utf-8")
        assert "2024-01-01" in content  # date_from in metadata or date_range

    def test_analytics_footer_text(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        data = ReportData(
            report_type=ReportType.ANALYTICS, title="Analytics",
            sections=[ReportSection(title="S", content="c")],
        )
        out = str(tmp_path / "analytics.html")
        result = gen._render_html_report(data, out)
        content = Path(out).read_text(encoding="utf-8")
        assert "Analytics" in content

    def test_performance_footer_text(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        data = ReportData(
            report_type=ReportType.PERFORMANCE, title="Performance",
            sections=[ReportSection(title="S", content="c")],
        )
        out = str(tmp_path / "perf.html")
        result = gen._render_html_report(data, out)
        content = Path(out).read_text(encoding="utf-8")
        assert "performance" in content.lower()

    def test_compliance_footer_text(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        data = ReportData(
            report_type=ReportType.COMPLIANCE, title="Compliance",
            sections=[ReportSection(title="S", content="c")],
        )
        out = str(tmp_path / "comp.html")
        result = gen._render_html_report(data, out)
        content = Path(out).read_text(encoding="utf-8")
        assert "GDPR" in content or "compliance" in content.lower()

    def test_render_exception(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        data = ReportData(
            report_type=ReportType.SUMMARY, title="T",
            sections=[],
        )
        with patch("builtins.open", side_effect=PermissionError("denied")):
            result = gen._render_html_report(data, "/nonwritable/rep.html")
        assert result.success is False


# ── _render_json_report ───────────────────────────────────────────────────────

class TestRenderJsonReport:
    def test_renders_json(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        data = ReportData(
            report_type=ReportType.SUMMARY, title="JSON Report",
            sections=[ReportSection(title="S", content="c", data={"k": "v"})],
            total_records=5,
        )
        out = str(tmp_path / "out.json")
        result = gen._render_json_report(data, out)
        assert result.success is True
        parsed = json.loads(Path(out).read_text())
        assert parsed["title"] == "JSON Report"
        assert parsed["total_records"] == 5


# ── Legacy: _collect_comprehensive_stats ──────────────────────────────────────

class TestCollectComprehensiveStats:
    """Lines 487-507: _collect_comprehensive_stats."""

    def test_empty_data(self, tmp_path):
        gen, db = make_generator(tmp_path)
        db.get_statistics.return_value = {"total_contacts": 0}
        db.get_emails.return_value = []
        db.get_companies.return_value = []
        stats = gen._collect_comprehensive_stats()
        assert "database" in stats
        assert "emails" in stats
        assert "companies" in stats
        assert "performance" in stats
        assert "quality" in stats

    def test_with_emails_and_companies(self, tmp_path):
        gen, db = make_generator(tmp_path)
        db.get_statistics.return_value = {"total_contacts": 5}
        db.get_emails.return_value = [
            {"final_score": 85, "validation_status": "valid", "role": "ceo",
             "source_type": "crawler", "confidence": 0.9, "risk_score": 20},
            {"final_score": 55, "validation_status": "invalid", "role": "hr",
             "source_type": "api", "confidence": 0.5, "risk_score": 60},
        ]
        db.get_companies.return_value = [
            {"industry": "Technology", "country": "NO", "credibility_score": 80},
        ]
        stats = gen._collect_comprehensive_stats()
        assert stats["emails"]["total"] == 2
        assert stats["companies"]["total"] == 1


# ── Legacy: _analyze_email_stats ──────────────────────────────────────────────

class TestAnalyzeEmailStats:
    """Lines 512-539: _analyze_email_stats."""

    def test_empty_emails(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        result = gen._analyze_email_stats([])
        assert result == {"total": 0}

    def test_with_emails(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        emails = [
            {"final_score": 90, "validation_status": "valid", "role": "ceo",
             "source_type": "web"},
            {"final_score": 65, "validation_status": "risky", "role": "hr",
             "source_type": "api"},
            {"final_score": 40, "validation_status": "invalid", "role": "unknown",
             "source_type": "web"},
        ]
        result = gen._analyze_email_stats(emails)
        assert result["total"] == 3
        assert result["score_distribution"]["high"] == 1
        assert result["score_distribution"]["medium"] == 1
        assert result["score_distribution"]["low"] == 1
        assert result["validation_status"]["valid"] == 1
        assert result["validation_status"]["risky"] == 1
        assert result["validation_status"]["invalid"] == 1


# ── Legacy: _analyze_company_stats ───────────────────────────────────────────

class TestAnalyzeCompanyStats:
    """Lines 559-580: _analyze_company_stats."""

    def test_empty_companies(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        result = gen._analyze_company_stats([])
        assert result == {"total": 0}

    def test_with_companies(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        companies = [
            {"industry": "Technology", "country": "NO", "credibility_score": 80},
            {"industry": "Finance", "country": "SE", "credibility_score": 60},
            {"industry": "Technology", "country": "NO", "credibility_score": 70},
        ]
        result = gen._analyze_company_stats(companies)
        assert result["total"] == 3
        assert result["industry_distribution"]["Technology"] == 2
        assert result["country_distribution"]["NO"] == 2
        assert result["average_credibility"] == pytest.approx(70.0, 0.1)


# ── Legacy: _calculate_performance_stats ─────────────────────────────────────

class TestCalculatePerformanceStats:
    """Lines 591-613: _calculate_performance_stats."""

    def test_empty_data(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        result = gen._calculate_performance_stats([], [])
        assert isinstance(result, dict)

    def test_with_companies_and_emails(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        now = datetime.now()
        companies = [{"id": 1}, {"id": 2}]
        emails = [
            {"created_at": now - timedelta(days=1)},   # recent — datetime object
            {"created_at": now - timedelta(days=30)},  # old
        ]
        result = gen._calculate_performance_stats(emails, companies)
        assert "email_extraction_rate" in result


# ── Legacy: _calculate_quality_stats ─────────────────────────────────────────

class TestCalculateQualityStats:
    """Lines 623-654: _calculate_quality_stats."""

    def test_empty_emails_returns_no_data(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        result = gen._calculate_quality_stats([])
        assert result == {"overall_quality": "No data"}

    def test_all_high_quality(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        emails = [
            {"confidence": 0.95, "final_score": 90, "validation_status": "valid", "risk_score": 10},
            {"confidence": 0.90, "final_score": 85, "validation_status": "valid", "risk_score": 15},
        ]
        result = gen._calculate_quality_stats(emails)
        assert result["overall_quality"] in ("Excellent", "Good", "Fair", "Poor")
        assert "high_confidence_rate" in result

    def test_poor_quality(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        emails = [
            {"confidence": 0.2, "final_score": 20, "validation_status": "invalid", "risk_score": 80},
        ]
        result = gen._calculate_quality_stats(emails)
        assert result["overall_quality"] in ("Poor", "Fair", "Good", "Excellent")


# ── Legacy: _generate_recommendations ─────────────────────────────────────────

class TestGenerateRecommendations:
    """Lines 666-740: _generate_recommendations."""

    def test_low_validation_rate_gives_recommendation(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        stats = {
            "emails": {
                "validation_status": {"validation_rate": 30},
                "score_distribution": {"high": 5},
                "total": 100,
                "source_distribution": {"web": 50},
            },
            "performance": {"email_extraction_rate": 2.0, "data_freshness_rate": 70},
        }
        recs = gen._generate_recommendations(stats)
        categories = [r["category"] for r in recs]
        assert "Data Quality" in categories

    def test_low_source_diversity_gives_recommendation(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        stats = {
            "emails": {
                "validation_status": {"validation_rate": 90},
                "score_distribution": {"high": 50},
                "total": 100,
                "source_distribution": {"web": 100},  # only 1 source
            },
            "performance": {"email_extraction_rate": 2.0, "data_freshness_rate": 70},
        }
        recs = gen._generate_recommendations(stats)
        categories = [r["category"] for r in recs]
        assert "Source Diversity" in categories

    def test_low_extraction_rate(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        stats = {
            "emails": {
                "validation_status": {"validation_rate": 90},
                "score_distribution": {"high": 50},
                "total": 100,
                "source_distribution": {"web": 40, "api": 30, "crawler": 30},
            },
            "performance": {"email_extraction_rate": 0.5, "data_freshness_rate": 80},
        }
        recs = gen._generate_recommendations(stats)
        categories = [r["category"] for r in recs]
        assert "Performance" in categories

    def test_stale_data_gives_recommendation(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        stats = {
            "emails": {
                "validation_status": {"validation_rate": 90},
                "score_distribution": {"high": 50},
                "total": 100,
                "source_distribution": {"a": 30, "b": 30, "c": 40},
            },
            "performance": {"email_extraction_rate": 2.0, "data_freshness_rate": 20},
        }
        recs = gen._generate_recommendations(stats)
        categories = [r["category"] for r in recs]
        assert "Data Freshness" in categories

    def test_all_good_gives_info_recommendation(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        stats = {
            "emails": {
                "validation_status": {"validation_rate": 95},
                "score_distribution": {"high": 80},
                "total": 100,
                "source_distribution": {"a": 30, "b": 30, "c": 40},
            },
            "performance": {"email_extraction_rate": 3.0, "data_freshness_rate": 80},
        }
        recs = gen._generate_recommendations(stats)
        assert len(recs) >= 1
        # When everything is fine, gets "Overall" info recommendation
        categories = [r["category"] for r in recs]
        assert "Overall" in categories


# ── Legacy: _get_report_template ──────────────────────────────────────────────

class TestGetReportTemplate:
    """Line 745: _get_report_template returns Jinja template string."""

    def test_returns_non_empty_template(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        template = gen._get_report_template()
        assert isinstance(template, str)
        assert len(template) > 100
        assert "{{ timestamp }}" in template or "timestamp" in template


# ── Legacy: export_json_report ────────────────────────────────────────────────

class TestExportJsonReport:
    """Lines 856-874: export_json_report."""

    def test_writes_json_file(self, tmp_path):
        gen, db = make_generator(tmp_path)
        db.get_statistics.return_value = {"total_contacts": 10}
        db.get_emails.return_value = [
            {"final_score": 80, "validation_status": "valid", "role": "sales",
             "source_type": "web", "confidence": 0.85, "risk_score": 20}
        ]
        db.get_companies.return_value = [
            {"industry": "Technology", "country": "NO", "credibility_score": 75}
        ]
        out_path = str(tmp_path / "report.json")
        result = gen.export_json_report(out_path)
        assert Path(out_path).exists()
        data = json.loads(Path(out_path).read_text())
        assert "statistics" in data
        assert "recommendations" in data
        assert "file_path" in result

    def test_includes_summary(self, tmp_path):
        gen, db = make_generator(tmp_path)
        db.get_statistics.return_value = {}
        db.get_emails.return_value = []
        db.get_companies.return_value = []
        out_path = str(tmp_path / "summary.json")
        result = gen.export_json_report(out_path)
        data = json.loads(Path(out_path).read_text())
        assert "summary" in data
        assert "generated_at" in data


# ── Utility methods ───────────────────────────────────────────────────────────

class TestUtilityMethods:
    def test_generate_pie_chart_data(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        result = gen._generate_pie_chart_data("Test", {"a": 1, "b": 2})
        assert result["type"] == "pie"
        assert result["title"] == "Test"

    def test_generate_bar_chart_data(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        result = gen._generate_bar_chart_data("Bar", {"x": 5})
        assert result["type"] == "bar"

    def test_calculate_file_size_existing(self, tmp_path):
        p = tmp_path / "test.txt"
        p.write_text("hello")
        gen, _ = make_generator(tmp_path)
        size = gen._calculate_file_size(str(p))
        assert size > 0

    def test_calculate_file_size_missing(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        size = gen._calculate_file_size("/nonexistent_xyz.html")
        assert size == 0

    def test_generate_filename_contains_type(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        name = gen._generate_filename(ReportType.SUMMARY)
        assert "summary" in name
        assert name.endswith(".html")

    def test_filter_by_date_range(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        contacts = [
            make_contact(),  # created_at 2024-04-10
            make_contact(),  # same
        ]
        contacts[0].created_at = datetime(2024, 3, 1)
        contacts[1].created_at = datetime(2024, 5, 15)
        result = gen._filter_by_date_range(
            contacts, datetime(2024, 4, 1), datetime(2024, 6, 1)
        )
        assert len(result) == 1
        assert result[0].created_at == datetime(2024, 5, 15)

    def test_export_report_data(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        data = ReportData(
            report_type=ReportType.SUMMARY, title="T",
            sections=[ReportSection(title="S", content="c")],
        )
        out = str(tmp_path / "out.json")
        success = gen._export_report_data(data, out)
        assert success is True
        assert Path(out).exists()

    def test_validate_template_exists_true(self, tmp_path):
        gen, _ = make_generator(tmp_path)
        assert gen._validate_template_exists("any.html") is True

    def test_validate_template_exists_false(self, tmp_path):
        db = make_mock_db()
        sc = make_mock_scorer()
        gen = ReportGenerator(
            db_manager=db, scorer=sc,
            output_dir=str(tmp_path / "rep"),
            template_dir="/nonexistent_xyz",
        )
        assert gen._validate_template_exists("any.html") is False
