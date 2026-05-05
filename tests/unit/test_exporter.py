"""
Unit tests for data export functionality
"""

import pytest
import tempfile
import shutil
import csv
import json
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

from export.exporter import DataExporter, ExportFormat, ExportResult, ExportFilter
from core.database import Contact, ContactStatus
from scoring.scorer import ScoreResult, PersonaMatch


class TestExportFormat:
    """Test ExportFormat enum"""

    def test_export_format_values(self):
        """Test export format enumeration values"""
        assert ExportFormat.CSV.value == "csv"
        assert ExportFormat.JSON.value == "json"
        assert ExportFormat.XLSX.value == "xlsx"
        assert ExportFormat.XML.value == "xml"


class TestExportFilter:
    """Test ExportFilter dataclass"""

    def test_export_filter_creation(self):
        """Test creating an export filter"""
        filter_obj = ExportFilter(
            status_filter=[ContactStatus.VALIDATED, ContactStatus.CONTACTED],
            min_score=0.7,
            max_score=1.0,
            domains=["company.com", "enterprise.com"],
            personas=["technical_leaders"],
            date_from=datetime(2024, 1, 1),
            date_to=datetime(2024, 12, 31),
            limit=1000
        )

        assert len(filter_obj.status_filter) == 2
        assert ContactStatus.VALIDATED in filter_obj.status_filter
        assert filter_obj.min_score == 0.7
        assert filter_obj.max_score == 1.0
        assert "company.com" in filter_obj.domains
        assert "technical_leaders" in filter_obj.personas
        assert filter_obj.date_from == datetime(2024, 1, 1)
        assert filter_obj.date_to == datetime(2024, 12, 31)
        assert filter_obj.limit == 1000

    def test_export_filter_defaults(self):
        """Test export filter with default values"""
        filter_obj = ExportFilter()

        assert filter_obj.status_filter is None
        assert filter_obj.min_score is None
        assert filter_obj.max_score is None
        assert filter_obj.domains is None
        assert filter_obj.personas is None
        assert filter_obj.date_from is None
        assert filter_obj.date_to is None
        assert filter_obj.limit is None


class TestExportResult:
    """Test ExportResult dataclass"""

    def test_export_result_creation(self):
        """Test creating an export result"""
        result = ExportResult(
            file_path="/path/to/export.csv",
            format=ExportFormat.CSV,
            total_records=150,
            filtered_records=120,
            file_size=2048,
            export_time=3.5,
            success=True
        )

        assert result.file_path == "/path/to/export.csv"
        assert result.format == ExportFormat.CSV
        assert result.total_records == 150
        assert result.filtered_records == 120
        assert result.file_size == 2048
        assert result.export_time == 3.5
        assert result.success is True
        assert result.error is None
        assert result.timestamp is not None

    def test_export_result_with_error(self):
        """Test export result with error"""
        result = ExportResult(
            file_path="/path/to/export.csv",
            format=ExportFormat.CSV,
            success=False,
            error="Permission denied"
        )

        assert result.file_path == "/path/to/export.csv"
        assert result.format == ExportFormat.CSV
        assert result.success is False
        assert result.error == "Permission denied"
        assert result.total_records == 0
        assert result.filtered_records == 0


class TestDataExporter:
    """Test DataExporter class"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test exports"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager"""
        db_manager = Mock()

        # Mock contacts data
        contacts = [
            Contact(
                email="cto@company1.com",
                domain="company1.com",
                name="John Smith",
                role="CTO",
                company="Company 1",
                sector="technology",
                confidence_score=0.9,
                status=ContactStatus.VALIDATED
            ),
            Contact(
                email="ceo@company2.com",
                domain="company2.com",
                name="Jane Doe",
                role="CEO",
                company="Company 2",
                sector="finance",
                confidence_score=0.8,
                status=ContactStatus.CONTACTED
            ),
            Contact(
                email="bounced@company3.com",
                domain="company3.com",
                name="Bob Wilson",
                role="Manager",
                company="Company 3",
                sector="retail",
                confidence_score=0.4,
                status=ContactStatus.BOUNCED
            )
        ]

        db_manager.get_all_contacts.return_value = contacts
        db_manager.get_contacts_by_status.return_value = contacts[:2]  # Exclude bounced

        return db_manager

    @pytest.fixture
    def mock_scorer(self):
        """Create a mock lead scorer"""
        scorer = Mock()

        # Mock scoring results
        def mock_score_contact(contact):
            if "cto" in contact.email:
                return ScoreResult(
                    contact_email=contact.email,
                    overall_score=0.85,
                    confidence=0.9,
                    best_persona="technical_leaders"
                )
            elif "ceo" in contact.email:
                return ScoreResult(
                    contact_email=contact.email,
                    overall_score=0.75,
                    confidence=0.8,
                    best_persona="executive_leaders"
                )
            else:
                return ScoreResult(
                    contact_email=contact.email,
                    overall_score=0.3,
                    confidence=0.4,
                    best_persona=None
                )

        scorer.score_contact.side_effect = mock_score_contact
        return scorer

    @pytest.fixture
    def exporter(self, mock_db_manager, mock_scorer, temp_dir):
        """Create a DataExporter instance for testing"""
        return DataExporter(
            db_manager=mock_db_manager,
            scorer=mock_scorer,
            output_dir=temp_dir
        )

    def test_exporter_initialization(self, exporter, mock_db_manager, mock_scorer, temp_dir):
        """Test exporter initialization"""
        assert exporter.db_manager == mock_db_manager
        assert exporter.scorer == mock_scorer
        assert exporter.output_dir == temp_dir
        assert exporter.default_columns is not None
        assert len(exporter.default_columns) > 0

    def test_exporter_default_initialization(self):
        """Test exporter with default parameters"""
        mock_db = Mock()
        mock_scorer = Mock()

        exporter = DataExporter(db_manager=mock_db, scorer=mock_scorer)

        assert exporter.db_manager == mock_db
        assert exporter.scorer == mock_scorer
        assert exporter.output_dir == "exports"
        assert Path(exporter.output_dir).exists()

    def test_export_csv_success(self, exporter, temp_dir):
        """Test successful CSV export"""
        output_file = Path(temp_dir) / "test_export.csv"

        result = exporter.export_to_csv(str(output_file))

        assert result.success is True
        assert result.format == ExportFormat.CSV
        assert result.total_records > 0
        assert result.file_path == str(output_file)
        assert output_file.exists()

        # Verify CSV content
        with open(output_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            assert len(rows) > 0
            assert 'email' in rows[0]
            assert 'name' in rows[0]
            assert 'company' in rows[0]

    def test_export_csv_with_filter(self, exporter, temp_dir):
        """Test CSV export with filtering"""
        output_file = Path(temp_dir) / "filtered_export.csv"
        filter_obj = ExportFilter(
            status_filter=[ContactStatus.VALIDATED, ContactStatus.CONTACTED],
            min_score=0.5
        )

        result = exporter.export_to_csv(str(output_file), filter_obj)

        assert result.success is True
        assert result.filtered_records <= result.total_records
        assert output_file.exists()

        # Verify filtered content
        with open(output_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            # Should exclude bounced contacts
            assert all(row['status'] != 'bounced' for row in rows)

    def test_export_json_success(self, exporter, temp_dir):
        """Test successful JSON export"""
        output_file = Path(temp_dir) / "test_export.json"

        result = exporter.export_to_json(str(output_file))

        assert result.success is True
        assert result.format == ExportFormat.JSON
        assert result.total_records > 0
        assert output_file.exists()

        # Verify JSON content
        with open(output_file, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
            assert isinstance(data, dict)
            assert 'contacts' in data
            assert 'export_metadata' in data
            assert len(data['contacts']) > 0
            assert 'email' in data['contacts'][0]

    def test_export_xlsx_success(self, exporter, temp_dir):
        """Test successful XLSX export"""
        output_file = Path(temp_dir) / "test_export.xlsx"

        with patch('pandas.DataFrame.to_excel') as mock_to_excel:
            result = exporter.export_to_xlsx(str(output_file))

            assert result.success is True
            assert result.format == ExportFormat.XLSX
            mock_to_excel.assert_called_once()

    def test_export_xml_success(self, exporter, temp_dir):
        """Test successful XML export"""
        output_file = Path(temp_dir) / "test_export.xml"

        result = exporter.export_to_xml(str(output_file))

        assert result.success is True
        assert result.format == ExportFormat.XML
        assert output_file.exists()

        # Verify XML content structure
        content = output_file.read_text(encoding='utf-8')
        assert '<?xml version="1.0" encoding="UTF-8"?>' in content
        assert '<contacts>' in content
        assert '<contact>' in content
        assert '</contacts>' in content

    def test_export_with_custom_columns(self, exporter, temp_dir):
        """Test export with custom column selection"""
        output_file = Path(temp_dir) / "custom_export.csv"
        custom_columns = ['email', 'name', 'company', 'overall_score']

        result = exporter.export_to_csv(str(output_file), columns=custom_columns)

        assert result.success is True
        assert output_file.exists()

        # Verify only specified columns are included
        with open(output_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            if rows:
                assert set(rows[0].keys()) == set(custom_columns)

    def test_export_file_permission_error(self, exporter):
        """Test export with file permission error"""
        # Try to write to a non-existent directory
        invalid_path = "/invalid/path/export.csv"

        result = exporter.export_to_csv(invalid_path)

        assert result.success is False
        assert result.error is not None
        assert "permission" in result.error.lower() or "no such file" in result.error.lower()

    def test_apply_filters(self, exporter):
        """Test filter application"""
        contacts = [
            Contact(email="valid@company.com", status=ContactStatus.VALIDATED, confidence_score=0.8),
            Contact(email="bounced@company.com", status=ContactStatus.BOUNCED, confidence_score=0.3),
            Contact(email="contacted@company.com", status=ContactStatus.CONTACTED, confidence_score=0.9)
        ]

        # Filter by status
        filter_obj = ExportFilter(status_filter=[ContactStatus.VALIDATED, ContactStatus.CONTACTED])
        filtered = exporter._apply_filters(contacts, filter_obj)
        assert len(filtered) == 2
        assert all(c.status != ContactStatus.BOUNCED for c in filtered)

        # Filter by confidence score
        filter_obj = ExportFilter(min_score=0.5)
        filtered = exporter._apply_filters(contacts, filter_obj)
        assert len(filtered) == 2
        assert all(c.confidence_score >= 0.5 for c in filtered)

    def test_apply_filters_domains(self, exporter):
        """Test domain filtering"""
        contacts = [
            Contact(email="user1@company.com", domain="company.com"),
            Contact(email="user2@enterprise.com", domain="enterprise.com"),
            Contact(email="user3@startup.com", domain="startup.com")
        ]

        filter_obj = ExportFilter(domains=["company.com", "enterprise.com"])
        filtered = exporter._apply_filters(contacts, filter_obj)

        assert len(filtered) == 2
        assert all(c.domain in ["company.com", "enterprise.com"] for c in filtered)

    def test_apply_filters_date_range(self, exporter):
        """Test date range filtering"""
        # Mock contacts with different creation dates
        old_date = datetime(2023, 1, 1)
        recent_date = datetime(2024, 6, 1)

        contacts = [
            Contact(email="old@company.com"),
            Contact(email="recent@company.com")
        ]

        # Manually set created_at for testing
        contacts[0].created_at = old_date
        contacts[1].created_at = recent_date

        filter_obj = ExportFilter(date_from=datetime(2024, 1, 1))
        filtered = exporter._apply_filters(contacts, filter_obj)

        # Should only include recent contact
        assert len(filtered) == 1
        assert filtered[0].email == "recent@company.com"

    def test_prepare_export_data(self, exporter):
        """Test export data preparation"""
        contacts = [
            Contact(
                email="test@company.com",
                name="Test User",
                role="Developer",
                company="Test Corp",
                status=ContactStatus.VALIDATED,
                confidence_score=0.8
            )
        ]

        data = exporter._prepare_export_data(contacts)

        assert len(data) == 1
        assert data[0]['email'] == "test@company.com"
        assert data[0]['name'] == "Test User"
        assert data[0]['role'] == "Developer"
        assert data[0]['company'] == "Test Corp"
        assert data[0]['status'] == "validated"
        assert 'overall_score' in data[0]  # Should include scoring data
        assert 'confidence' in data[0]

    def test_prepare_export_data_with_scoring(self, exporter):
        """Test export data preparation includes scoring results"""
        contacts = [
            Contact(email="cto@company.com", role="CTO")
        ]

        data = exporter._prepare_export_data(contacts)

        assert len(data) == 1
        assert data[0]['overall_score'] == 0.85  # From mock scorer
        assert data[0]['confidence'] == 0.9
        assert data[0]['persona_match'] == "technical_leaders"

    def test_generate_filename(self, exporter):
        """Test automatic filename generation"""
        # Test with extension
        filename = exporter._generate_filename("leads", ExportFormat.CSV)
        assert filename.startswith("leads_")
        assert filename.endswith(".csv")
        assert len(filename) > len("leads_.csv")  # Should include timestamp

        # Test different formats
        json_filename = exporter._generate_filename("data", ExportFormat.JSON)
        assert json_filename.endswith(".json")

        xlsx_filename = exporter._generate_filename("export", ExportFormat.XLSX)
        assert xlsx_filename.endswith(".xlsx")

    def test_get_file_size(self, exporter, temp_dir):
        """Test file size calculation"""
        test_file = Path(temp_dir) / "test_size.txt"
        test_content = "Hello, World!" * 100
        test_file.write_text(test_content)

        size = exporter._get_file_size(str(test_file))
        assert size > 0
        assert size == len(test_content.encode('utf-8'))

    def test_get_file_size_nonexistent(self, exporter):
        """Test file size calculation for non-existent file"""
        size = exporter._get_file_size("/nonexistent/file.txt")
        assert size == 0

    def test_export_batch_multiple_formats(self, exporter, temp_dir):
        """Test exporting to multiple formats"""
        base_name = "multi_export"
        formats = [ExportFormat.CSV, ExportFormat.JSON]

        results = exporter.export_batch(base_name, formats)

        assert len(results) == 2
        assert all(result.success for result in results)
        assert results[0].format == ExportFormat.CSV
        assert results[1].format == ExportFormat.JSON

        # Verify files were created
        csv_file = Path(temp_dir) / f"{base_name}.csv"
        json_file = Path(temp_dir) / f"{base_name}.json"
        # Note: Files might have timestamps in names, so we check if any CSV/JSON files exist
        csv_files = list(Path(temp_dir).glob("*.csv"))
        json_files = list(Path(temp_dir).glob("*.json"))
        assert len(csv_files) >= 1
        assert len(json_files) >= 1

    def test_export_with_metadata(self, exporter, temp_dir):
        """Test that exports include metadata"""
        output_file = Path(temp_dir) / "metadata_test.json"

        result = exporter.export_to_json(str(output_file))

        assert result.success is True

        with open(output_file, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
            metadata = data['export_metadata']

            assert 'export_date' in metadata
            assert 'total_records' in metadata
            assert 'export_format' in metadata
            assert 'system_version' in metadata
            assert metadata['export_format'] == 'json'

    def test_export_empty_dataset(self, exporter, temp_dir):
        """Test export with empty dataset"""
        # Mock empty contacts
        exporter.db_manager.get_all_contacts.return_value = []

        output_file = Path(temp_dir) / "empty_export.csv"
        result = exporter.export_to_csv(str(output_file))

        assert result.success is True
        assert result.total_records == 0
        assert result.filtered_records == 0
        assert output_file.exists()

        # Should still create file with headers
        with open(output_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
            assert len(rows) >= 1  # At least header row

    def test_validate_output_path(self, exporter, temp_dir):
        """Test output path validation"""
        # Valid path
        valid_path = Path(temp_dir) / "valid_export.csv"
        assert exporter._validate_output_path(str(valid_path)) is True

        # Invalid path (non-existent directory)
        invalid_path = "/non/existent/directory/export.csv"
        assert exporter._validate_output_path(invalid_path) is False

        # Path with no write permissions (mock)
        with patch('pathlib.Path.parent') as mock_parent:
            mock_parent.exists.return_value = True
            mock_parent.is_dir.return_value = True
            with patch('os.access', return_value=False):
                restricted_path = "/restricted/export.csv"
                assert exporter._validate_output_path(restricted_path) is False