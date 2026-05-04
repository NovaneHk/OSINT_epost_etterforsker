"""
Extended coverage tests for export/exporter.py
Targets uncovered lines: 35, 48, 95-96, 105, 130-131, 140, 145-146,
160-161, 165, 174, 194-195, 199-248, 259-266, 274, 288, 297, 300, 308,
331-338, 363-364, 368, 371, 374, 377, 380
"""
import pytest
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from export.exporter import DataExporter, ExportFormat, ExportFilter, ExportResult
from core.database import Contact, ContactStatus


def make_contact(email="x@example.com", domain="example.com", role="sales",
                 company="ACME", status=ContactStatus.VALIDATED,
                 confidence_score=0.85):
    c = MagicMock(spec=Contact)
    c.email = email
    c.domain = domain
    c.role = role
    c.company = company
    c.name = "Test User"
    c.sector = "Tech"
    c.status = status
    c.confidence_score = confidence_score
    c.overall_score = confidence_score
    c.persona_match = "CTO"
    c.created_at = datetime(2024, 3, 15)
    return c


def make_exporter(contacts=None, output_dir=None):
    db = MagicMock()
    db.get_all_contacts.return_value = contacts if contacts is not None else []
    with tempfile.TemporaryDirectory() as tmp:
        od = output_dir or tmp
        exp = DataExporter(db_manager=db, output_dir=od)
        exp._tmpdir = tmp  # keep alive reference for test scope
        return exp, db, od


# ── export_to_xml ─────────────────────────────────────────────────────────────

class TestExportToXml:
    """Lines 199-248: XML export path."""

    def test_basic_xml_export(self, tmp_path):
        contacts = [make_contact("a@b.com"), make_contact("c@d.com")]
        db = MagicMock()
        db.get_all_contacts.return_value = contacts
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        file_path = str(tmp_path / "contacts.xml")
        result = exp.export_to_xml(file_path)
        assert result.success is True
        assert Path(file_path).exists()
        content = Path(file_path).read_text()
        assert "<contacts>" in content
        assert "<contact>" in content

    def test_xml_with_filter(self, tmp_path):
        contacts = [make_contact(confidence_score=0.9), make_contact(confidence_score=0.3)]
        db = MagicMock()
        db.get_all_contacts.return_value = contacts
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        flt = ExportFilter(min_score=0.5)
        file_path = str(tmp_path / "filtered.xml")
        result = exp.export_to_xml(file_path, export_filter=flt)
        assert result.success is True
        assert result.filtered_records == 1

    def test_xml_invalid_path(self, tmp_path):
        db = MagicMock()
        db.get_all_contacts.return_value = [make_contact()]
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        result = exp.export_to_xml("/nonexistent_dir_xyz/contacts.xml")
        assert result.success is False


# ── export_to_maltego ─────────────────────────────────────────────────────────

class TestExportToMaltego:
    """Lines 259-266, 274, 288, 297, 300, 308: Maltego export."""

    def test_basic_maltego_export(self, tmp_path):
        contacts = [make_contact("boss@corp.com", company="Corp", role="executive")]
        db = MagicMock()
        db.get_all_contacts.return_value = contacts
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        file_path = str(tmp_path / "graph.mtgl")
        result = exp.export_to_maltego(file_path)
        assert result.success is True
        content = Path(file_path).read_text()
        assert "MaltegoMessage" in content
        assert "maltego.EmailAddress" in content
        assert "boss@corp.com" in content

    def test_maltego_includes_company_and_name(self, tmp_path):
        c = make_contact("ceo@test.com", company="TestCorp")
        db = MagicMock()
        db.get_all_contacts.return_value = [c]
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        file_path = str(tmp_path / "graph2.mtgl")
        result = exp.export_to_maltego(file_path)
        content = Path(file_path).read_text()
        assert "TestCorp" in content

    def test_maltego_invalid_path(self, tmp_path):
        db = MagicMock()
        db.get_all_contacts.return_value = [make_contact()]
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        result = exp.export_to_maltego("/bad/path/graph.mtgl")
        assert result.success is False

    def test_maltego_with_filter(self, tmp_path):
        contacts = [make_contact(confidence_score=0.9), make_contact(confidence_score=0.2)]
        db = MagicMock()
        db.get_all_contacts.return_value = contacts
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        flt = ExportFilter(min_score=0.5)
        result = exp.export_to_maltego(str(tmp_path / "flt.mtgl"), export_filter=flt)
        assert result.success is True
        assert result.filtered_records == 1


# ── export_to_xlsx ─────────────────────────────────────────────────────────────

class TestExportToXlsx:
    """Lines 130-131, 140, 145-146, 160-161, 165, 174: XLSX export."""

    def test_xlsx_export_without_pandas(self, tmp_path):
        """Test XLSX fallback path when pandas is None (uses JSON fallback)."""
        contacts = [make_contact()]
        db = MagicMock()
        db.get_all_contacts.return_value = contacts
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        file_path = str(tmp_path / "data.xlsx")
        with patch("export.exporter.pd", None):
            result = exp.export_to_xlsx(file_path)
        assert result.success is True
        assert Path(file_path).exists()

    def test_xlsx_with_pandas(self, tmp_path):
        """Test XLSX export with pandas mocked."""
        contacts = [make_contact()]
        db = MagicMock()
        db.get_all_contacts.return_value = contacts
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        file_path = str(tmp_path / "data.xlsx")
        mock_df = MagicMock()
        mock_pd = MagicMock()
        mock_pd.DataFrame.return_value = mock_df
        with patch("export.exporter.pd", mock_pd):
            result = exp.export_to_xlsx(file_path)
        # df.to_excel was called
        mock_df.to_excel.assert_called_once_with(file_path, index=False)

    def test_xlsx_invalid_path(self, tmp_path):
        db = MagicMock()
        db.get_all_contacts.return_value = [make_contact()]
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        result = exp.export_to_xlsx("/nonexistent/dir/data.xlsx")
        assert result.success is False

    def test_xlsx_via_alias_export_to_excel(self, tmp_path):
        contacts = [make_contact()]
        db = MagicMock()
        db.get_all_contacts.return_value = contacts
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        file_path = str(tmp_path / "alias.xlsx")
        with patch("export.exporter.pd", None):
            result = exp.export_to_excel(file_path)
        assert result.success is True


# ── _apply_filters edge cases ─────────────────────────────────────────────────

class TestApplyFilters:
    """Lines 331-338: filter branches for domain, date range, limit."""

    def test_filter_by_domain(self, tmp_path):
        c1 = make_contact("a@alpha.com", "alpha.com")
        c2 = make_contact("b@beta.com", "beta.com")
        db = MagicMock()
        db.get_all_contacts.return_value = [c1, c2]
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        flt = ExportFilter(domains=["alpha.com"])
        filtered = exp._apply_filters([c1, c2], flt)
        assert len(filtered) == 1
        assert filtered[0].domain == "alpha.com"

    def test_filter_by_date_from(self, tmp_path):
        c1 = make_contact(); c1.created_at = datetime(2024, 1, 10)
        c2 = make_contact(); c2.created_at = datetime(2024, 6, 10)
        db = MagicMock()
        db.get_all_contacts.return_value = [c1, c2]
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        flt = ExportFilter(date_from=datetime(2024, 3, 1))
        filtered = exp._apply_filters([c1, c2], flt)
        assert len(filtered) == 1

    def test_filter_by_date_to(self, tmp_path):
        c1 = make_contact(); c1.created_at = datetime(2024, 1, 10)
        c2 = make_contact(); c2.created_at = datetime(2024, 6, 10)
        db = MagicMock()
        db.get_all_contacts.return_value = [c1, c2]
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        flt = ExportFilter(date_to=datetime(2024, 3, 1))
        filtered = exp._apply_filters([c1, c2], flt)
        assert len(filtered) == 1

    def test_filter_limit(self, tmp_path):
        contacts = [make_contact(f"u{i}@x.com") for i in range(10)]
        db = MagicMock()
        db.get_all_contacts.return_value = contacts
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        flt = ExportFilter(limit=3)
        filtered = exp._apply_filters(contacts, flt)
        assert len(filtered) == 3

    def test_filter_max_score(self, tmp_path):
        c1 = make_contact(confidence_score=0.9)
        c2 = make_contact(confidence_score=0.3)
        db = MagicMock()
        db.get_all_contacts.return_value = [c1, c2]
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        flt = ExportFilter(max_score=0.5)
        filtered = exp._apply_filters([c1, c2], flt)
        assert len(filtered) == 1
        assert filtered[0].confidence_score == 0.3

    def test_filter_status(self, tmp_path):
        c1 = make_contact(status=ContactStatus.VALIDATED)
        c2 = make_contact(status=ContactStatus.BOUNCED)
        exp = DataExporter(db_manager=None, output_dir=str(tmp_path))
        flt = ExportFilter(status_filter=[ContactStatus.VALIDATED])
        filtered = exp._apply_filters([c1, c2], flt)
        assert len(filtered) == 1


# ── _prepare_export_data with scorer ─────────────────────────────────────────

class TestPrepareExportData:
    """Lines 363-364, 368, 371, 374, 377, 380: scorer branch."""

    def test_with_scorer(self, tmp_path):
        scorer = MagicMock()
        score_obj = MagicMock()
        score_obj.overall_score = 0.9
        score_obj.confidence = 0.95
        score_obj.best_persona = "CTO"
        scorer.score_contact.return_value = score_obj

        contacts = [make_contact()]
        exp = DataExporter(db_manager=None, scorer=scorer, output_dir=str(tmp_path))
        rows = exp._prepare_export_data(contacts)
        assert len(rows) == 1
        assert rows[0]["overall_score"] == 0.9
        assert rows[0]["persona_match"] == "CTO"

    def test_with_scorer_exception(self, tmp_path):
        scorer = MagicMock()
        scorer.score_contact.side_effect = Exception("scorer error")
        contacts = [make_contact()]
        exp = DataExporter(db_manager=None, scorer=scorer, output_dir=str(tmp_path))
        rows = exp._prepare_export_data(contacts)
        # Should not raise; falls back to None values
        assert len(rows) == 1


# ── export_batch ──────────────────────────────────────────────────────────────

class TestExportBatch:
    """Lines 199-248 via export_batch."""

    def test_batch_csv_and_json(self, tmp_path):
        contacts = [make_contact()]
        db = MagicMock()
        db.get_all_contacts.return_value = contacts
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        results = exp.export_batch("test", [ExportFormat.CSV, ExportFormat.JSON])
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_batch_xml_and_maltego(self, tmp_path):
        contacts = [make_contact()]
        db = MagicMock()
        db.get_all_contacts.return_value = contacts
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        results = exp.export_batch("b", [ExportFormat.XML, ExportFormat.MALTEGO])
        assert len(results) == 2

    def test_batch_xlsx(self, tmp_path):
        contacts = [make_contact()]
        db = MagicMock()
        db.get_all_contacts.return_value = contacts
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        with patch("export.exporter.pd", None):
            results = exp.export_batch("b", [ExportFormat.XLSX])
        assert len(results) == 1

    def test_batch_unsupported_format(self, tmp_path):
        db = MagicMock()
        db.get_all_contacts.return_value = []
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        # Sneak an unknown format value in
        fake_fmt = MagicMock()
        fake_fmt.__class__ = ExportFormat
        fake_fmt.value = "unknown"
        results = exp.export_batch("b", [fake_fmt])
        assert results[0].success is False


# ── export_to_json with invalid path ─────────────────────────────────────────

class TestExportToJson:
    """Lines 95-96, 105: JSON permission denied / exception paths."""

    def test_invalid_path_returns_failure(self, tmp_path):
        db = MagicMock()
        db.get_all_contacts.return_value = [make_contact()]
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        result = exp.export_to_json("/nonexistent_xyz/data.json")
        assert result.success is False

    def test_exception_in_open_returns_failure(self, tmp_path):
        db = MagicMock()
        db.get_all_contacts.return_value = [make_contact()]
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        with patch("builtins.open", side_effect=PermissionError("denied")):
            with patch.object(exp, "_validate_output_path", return_value=True):
                result = exp.export_to_json(str(tmp_path / "data.json"))
        assert result.success is False


# ── export_to_csv extra branches ──────────────────────────────────────────────

class TestExportToCsvExtra:
    """Lines 35, 48: various CSV paths."""

    def test_csv_with_columns_filter(self, tmp_path):
        contacts = [make_contact()]
        db = MagicMock()
        db.get_all_contacts.return_value = contacts
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        file_path = str(tmp_path / "partial.csv")
        result = exp.export_to_csv(file_path, columns=["email", "domain"])
        assert result.success is True
        content = Path(file_path).read_text()
        assert "email" in content
        assert "domain" in content

    def test_csv_exception_returns_failure(self, tmp_path):
        db = MagicMock()
        db.get_all_contacts.return_value = [make_contact()]
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        with patch("builtins.open", side_effect=IOError("disk full")):
            with patch.object(exp, "_validate_output_path", return_value=True):
                result = exp.export_to_csv(str(tmp_path / "x.csv"))
        assert result.success is False


# ── _get_contacts without db_manager ─────────────────────────────────────────

class TestGetContacts:
    def test_no_db_returns_empty(self, tmp_path):
        exp = DataExporter(db_manager=None, output_dir=str(tmp_path))
        contacts = exp._get_contacts()
        assert contacts == []

    def test_db_without_get_all_contacts(self, tmp_path):
        db = MagicMock(spec=[])
        exp = DataExporter(db_manager=db, output_dir=str(tmp_path))
        contacts = exp._get_contacts()
        assert contacts == []


# ── Public helper aliases ─────────────────────────────────────────────────────

class TestPublicHelpers:
    def test_generate_filename(self, tmp_path):
        exp = DataExporter(db_manager=None, output_dir=str(tmp_path))
        name = exp.generate_filename("export", ExportFormat.CSV)
        assert name.endswith(".csv")
        assert "export" in name

    def test_get_file_size_existing(self, tmp_path):
        p = tmp_path / "test.txt"
        p.write_text("hello world")
        exp = DataExporter(db_manager=None, output_dir=str(tmp_path))
        size = exp.get_file_size(str(p))
        assert size > 0

    def test_get_file_size_missing(self, tmp_path):
        exp = DataExporter(db_manager=None, output_dir=str(tmp_path))
        size = exp.get_file_size("/nonexistent_file_xyz.bin")
        assert size == 0

    def test_validate_output_path_valid(self, tmp_path):
        exp = DataExporter(db_manager=None, output_dir=str(tmp_path))
        assert exp.validate_output_path(str(tmp_path / "file.csv")) is True

    def test_validate_output_path_invalid(self, tmp_path):
        exp = DataExporter(db_manager=None, output_dir=str(tmp_path))
        assert exp.validate_output_path("/nonexistent_dir_xyz/file.csv") is False

    def test_apply_filters_none_filter(self, tmp_path):
        contacts = [make_contact(), make_contact()]
        exp = DataExporter(db_manager=None, output_dir=str(tmp_path))
        result = exp.apply_filters(contacts, None)
        assert len(result) == 2
