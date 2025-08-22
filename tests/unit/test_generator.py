"""
Unit tests for report generation functionality
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

from report.generator import ReportGenerator, ReportType, ReportData, ReportResult, ReportSection
from core.database import Contact, ContactStatus
from scoring.scorer import ScoreResult, PersonaMatch


class TestReportType:
    """Test ReportType enum"""

    def test_report_type_values(self):
        """Test report type enumeration values"""
        assert ReportType.SUMMARY.value == "summary"
        assert ReportType.DETAILED.value == "detailed"
        assert ReportType.ANALYTICS.value == "analytics"
        assert ReportType.PERFORMANCE.value == "performance"
        assert ReportType.COMPLIANCE.value == "compliance"


class TestReportSection:
    """Test ReportSection dataclass"""

    def test_report_section_creation(self):
        """Test creating a report section"""
        section = ReportSection(
            title="Contact Summary",
            content="Overview of contact data",
            data={"total_contacts": 150, "validated": 120},
            charts=["contact_status_pie", "domain_distribution"],
            order=1
        )

        assert section.title == "Contact Summary"
        assert section.content == "Overview of contact data"
        assert section.data["total_contacts"] == 150
        assert "contact_status_pie" in section.charts
        assert section.order == 1

    def test_report_section_defaults(self):
        """Test report section with default values"""
        section = ReportSection(
            title="Test Section",
            content="Test content"
        )

        assert section.title == "Test Section"
        assert section.content == "Test content"
        assert section.data == {}
        assert section.charts == []
        assert section.order == 0


class TestReportData:
    """Test ReportData dataclass"""

    def test_report_data_creation(self):
        """Test creating report data"""
        sections = [
            ReportSection(title="Summary", content="Overview"),
            ReportSection(title="Details", content="Detailed analysis")
        ]

        metadata = {
            "generated_at": datetime.now(),
            "generated_by": "system",
            "report_version": "1.0"
        }

        data = ReportData(
            report_type=ReportType.SUMMARY,
            title="Monthly Contact Report",
            description="Summary of contact activities",
            sections=sections,
            metadata=metadata,
            total_records=500,
            date_range=("2024-01-01", "2024-01-31")
        )

        assert data.report_type == ReportType.SUMMARY
        assert data.title == "Monthly Contact Report"
        assert data.description == "Summary of contact activities"
        assert len(data.sections) == 2
        assert data.total_records == 500
        assert data.date_range == ("2024-01-01", "2024-01-31")
        assert "generated_at" in data.metadata


class TestReportResult:
    """Test ReportResult dataclass"""

    def test_report_result_creation(self):
        """Test creating report result"""
        result = ReportResult(
            report_path="/path/to/report.html",
            report_type=ReportType.DETAILED,
            generation_time=5.2,
            file_size=2048,
            success=True,
            sections_count=8
        )

        assert result.report_path == "/path/to/report.html"
        assert result.report_type == ReportType.DETAILED
        assert result.generation_time == 5.2
        assert result.file_size == 2048
        assert result.success is True
        assert result.sections_count == 8
        assert result.error is None
        assert result.timestamp is not None

    def test_report_result_with_error(self):
        """Test report result with error"""
        result = ReportResult(
            report_path="/path/to/report.html",
            report_type=ReportType.SUMMARY,
            success=False,
            error="Template not found"
        )

        assert result.report_path == "/path/to/report.html"
        assert result.report_type == ReportType.SUMMARY
        assert result.success is False
        assert result.error == "Template not found"
        assert result.generation_time == 0.0
        assert result.file_size == 0


class TestReportGenerator:
    """Test ReportGenerator class"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test reports"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager"""
        db_manager = Mock()

        # Mock contact data
        contacts = [
            Contact(
                email="cto@company1.com",
                domain="company1.com",
                name="John Smith",
                role="CTO",
                company="Company 1",
                sector="technology",
                status=ContactStatus.VALIDATED,
                confidence_score=0.9
            ),
            Contact(
                email="ceo@company2.com",
                domain="company2.com",
                name="Jane Doe",
                role="CEO",
                company="Company 2",
                sector="finance",
                status=ContactStatus.CONTACTED,
                confidence_score=0.8
            ),
            Contact(
                email="bounced@company3.com",
                domain="company3.com",
                name="Bob Wilson",
                role="Manager",
                company="Company 3",
                sector="retail",
                status=ContactStatus.BOUNCED,
                confidence_score=0.4
            )
        ]

        db_manager.get_all_contacts.return_value = contacts
        db_manager.get_contact_stats.return_value = {
            'total': 3,
            'validated': 1,
            'contacted': 1,
            'bounced': 1,
            'unvalidated': 0,
            'responded': 0,
            'opted_out': 0
        }

        return db_manager

    @pytest.fixture
    def mock_scorer(self):
        """Create mock lead scorer"""
        scorer = Mock()

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
    def generator(self, mock_db_manager, mock_scorer, temp_dir):
        """Create ReportGenerator instance for testing"""
        return ReportGenerator(
            db_manager=mock_db_manager,
            scorer=mock_scorer,
            output_dir=temp_dir,
            template_dir="templates"
        )

    def test_generator_initialization(self, generator, mock_db_manager, mock_scorer, temp_dir):
        """Test generator initialization"""
        assert generator.db_manager == mock_db_manager
        assert generator.scorer == mock_scorer
        assert generator.output_dir == temp_dir
        assert generator.template_dir == "templates"
        assert Path(generator.output_dir).exists()

    def test_generator_default_initialization(self):
        """Test generator with default parameters"""
        mock_db = Mock()
        mock_scorer = Mock()

        generator = ReportGenerator(db_manager=mock_db, scorer=mock_scorer)

        assert generator.db_manager == mock_db
        assert generator.scorer == mock_scorer
        assert generator.output_dir == "reports"
        assert generator.template_dir == "templates"

    def test_generate_summary_report(self, generator, temp_dir):
        """Test generating summary report"""
        result = generator.generate_summary_report()

        assert result.success is True
        assert result.report_type == ReportType.SUMMARY
        assert result.sections_count > 0
        assert result.generation_time > 0

        # Verify report file was created
        report_path = Path(result.report_path)
        assert report_path.exists()
        assert report_path.suffix == ".html"

    def test_generate_detailed_report(self, generator, temp_dir):
        """Test generating detailed report"""
        result = generator.generate_detailed_report()

        assert result.success is True
        assert result.report_type == ReportType.DETAILED
        assert result.sections_count > 0

        # Detailed report should have more sections than summary
        summary_result = generator.generate_summary_report()
        assert result.sections_count >= summary_result.sections_count

    def test_generate_analytics_report(self, generator, temp_dir):
        """Test generating analytics report"""
        result = generator.generate_analytics_report()

        assert result.success is True
        assert result.report_type == ReportType.ANALYTICS
        assert result.sections_count > 0

        # Should include analytics-specific sections
        with open(result.report_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Analytics" in content or "analytics" in content

    def test_generate_performance_report(self, generator):
        """Test generating performance report"""
        result = generator.generate_performance_report()

        assert result.success is True
        assert result.report_type == ReportType.PERFORMANCE

        # Performance report should include metrics
        with open(result.report_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "performance" in content.lower() or "metrics" in content.lower()

    def test_generate_compliance_report(self, generator):
        """Test generating compliance report"""
        result = generator.generate_compliance_report()

        assert result.success is True
        assert result.report_type == ReportType.COMPLIANCE

        # Compliance report should include GDPR/privacy information
        with open(result.report_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "compliance" in content.lower() or "gdpr" in content.lower()

    def test_collect_summary_data(self, generator):
        """Test collecting data for summary report"""
        data = generator._collect_summary_data()

        assert isinstance(data, ReportData)
        assert data.report_type == ReportType.SUMMARY
        assert len(data.sections) > 0
        assert data.total_records > 0

        # Check for expected summary sections
        section_titles = [section.title for section in data.sections]
        assert any("Contact" in title for title in section_titles)
        assert any("Status" in title or "Overview" in title for title in section_titles)

    def test_collect_detailed_data(self, generator):
        """Test collecting data for detailed report"""
        data = generator._collect_detailed_data()

        assert isinstance(data, ReportData)
        assert data.report_type == ReportType.DETAILED
        assert len(data.sections) > 0

        # Detailed report should have more sections
        summary_data = generator._collect_summary_data()
        assert len(data.sections) >= len(summary_data.sections)

    def test_collect_analytics_data(self, generator):
        """Test collecting data for analytics report"""
        data = generator._collect_analytics_data()

        assert isinstance(data, ReportData)
        assert data.report_type == ReportType.ANALYTICS
        assert len(data.sections) > 0

        # Should include analytics-specific sections
        section_titles = [section.title for section in data.sections]
        assert any("Score" in title or "Performance" in title for title in section_titles)

    def test_create_contact_overview_section(self, generator):
        """Test creating contact overview section"""
        section = generator._create_contact_overview_section()

        assert isinstance(section, ReportSection)
        assert "Contact" in section.title or "Overview" in section.title
        assert "total_contacts" in section.data
        assert section.data["total_contacts"] > 0
        assert len(section.charts) > 0

    def test_create_status_distribution_section(self, generator):
        """Test creating status distribution section"""
        section = generator._create_status_distribution_section()

        assert isinstance(section, ReportSection)
        assert "Status" in section.title or "Distribution" in section.title
        assert "status_counts" in section.data
        assert "pie_chart" in section.charts or "bar_chart" in section.charts

    def test_create_domain_analysis_section(self, generator):
        """Test creating domain analysis section"""
        section = generator._create_domain_analysis_section()

        assert isinstance(section, ReportSection)
        assert "Domain" in section.title
        assert "domain_stats" in section.data
        assert len(section.data["domain_stats"]) > 0

    def test_create_scoring_analysis_section(self, generator):
        """Test creating scoring analysis section"""
        section = generator._create_scoring_analysis_section()

        assert isinstance(section, ReportSection)
        assert "Score" in section.title or "Scoring" in section.title
        assert "score_distribution" in section.data
        assert "average_score" in section.data

    def test_create_persona_analysis_section(self, generator):
        """Test creating persona analysis section"""
        section = generator._create_persona_analysis_section()

        assert isinstance(section, ReportSection)
        assert "Persona" in section.title
        assert "persona_distribution" in section.data

    def test_generate_chart_data(self, generator):
        """Test chart data generation"""
        # Test pie chart data
        pie_data = generator._generate_pie_chart_data("Contact Status", {
            "validated": 50,
            "contacted": 30,
            "bounced": 20
        })

        assert isinstance(pie_data, dict)
        assert "type" in pie_data
        assert "data" in pie_data
        assert pie_data["type"] == "pie"

        # Test bar chart data
        bar_data = generator._generate_bar_chart_data("Domain Distribution", {
            "company1.com": 15,
            "company2.com": 10,
            "company3.com": 8
        })

        assert isinstance(bar_data, dict)
        assert bar_data["type"] == "bar"

    def test_render_html_report(self, generator, temp_dir):
        """Test HTML report rendering"""
        # Create test report data
        sections = [
            ReportSection(title="Test Section", content="Test content", data={"test": 123})
        ]

        report_data = ReportData(
            report_type=ReportType.SUMMARY,
            title="Test Report",
            description="Test description",
            sections=sections,
            metadata={"generated_at": datetime.now()},
            total_records=100
        )

        output_path = Path(temp_dir) / "test_report.html"
        result = generator._render_html_report(report_data, str(output_path))

        assert result.success is True
        assert output_path.exists()

        # Verify HTML content
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "<html" in content
            assert "Test Report" in content
            assert "Test Section" in content

    def test_render_json_report(self, generator, temp_dir):
        """Test JSON report rendering"""
        sections = [
            ReportSection(title="Test Section", content="Test content", data={"test": 123})
        ]

        report_data = ReportData(
            report_type=ReportType.SUMMARY,
            title="Test Report",
            sections=sections,
            total_records=100
        )

        output_path = Path(temp_dir) / "test_report.json"
        result = generator._render_json_report(report_data, str(output_path))

        assert result.success is True
        assert output_path.exists()

        # Verify JSON content
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert data["title"] == "Test Report"
            assert len(data["sections"]) == 1
            assert data["sections"][0]["title"] == "Test Section"

    def test_calculate_file_size(self, generator, temp_dir):
        """Test file size calculation"""
        test_file = Path(temp_dir) / "test_size.txt"
        test_content = "Hello, World!" * 100
        test_file.write_text(test_content)

        size = generator._calculate_file_size(str(test_file))
        assert size > 0
        assert size == len(test_content.encode('utf-8'))

    def test_generate_filename(self, generator):
        """Test filename generation"""
        filename = generator._generate_filename(ReportType.SUMMARY)

        assert filename.startswith("summary_report_")
        assert filename.endswith(".html")
        assert len(filename) > len("summary_report_.html")  # Should include timestamp

        # Test JSON format
        json_filename = generator._generate_filename(ReportType.ANALYTICS, format_type="json")
        assert json_filename.endswith(".json")

    def test_get_date_range_filter(self, generator):
        """Test date range filtering"""
        # Test with custom date range
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        contacts = generator.db_manager.get_all_contacts()

        # Mock created_at dates
        contacts[0].created_at = datetime(2024, 1, 15)  # Within range
        contacts[1].created_at = datetime(2023, 12, 15)  # Before range
        contacts[2].created_at = datetime(2024, 2, 15)  # After range

        filtered = generator._filter_by_date_range(contacts, start_date, end_date)
        assert len(filtered) == 1
        assert filtered[0].email == "cto@company1.com"

    def test_export_report_data(self, generator, temp_dir):
        """Test exporting raw report data"""
        sections = [
            ReportSection(title="Test", content="Content", data={"value": 42})
        ]

        report_data = ReportData(
            report_type=ReportType.SUMMARY,
            title="Test Export",
            sections=sections,
            total_records=10
        )

        export_path = Path(temp_dir) / "export_data.json"
        success = generator._export_report_data(report_data, str(export_path))

        assert success is True
        assert export_path.exists()

        # Verify exported data
        with open(export_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert data["title"] == "Test Export"
            assert data["total_records"] == 10

    def test_validate_template_exists(self, generator):
        """Test template existence validation"""
        # This would normally check if templates exist
        # For testing, we mock the validation
        with patch('pathlib.Path.exists', return_value=True):
            assert generator._validate_template_exists("summary.html") is True

        with patch('pathlib.Path.exists', return_value=False):
            assert generator._validate_template_exists("nonexistent.html") is False

    def test_generate_report_with_custom_date_range(self, generator):
        """Test report generation with custom date range"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        result = generator.generate_summary_report(
            date_from=start_date,
            date_to=end_date
        )

        assert result.success is True
        assert result.report_type == ReportType.SUMMARY

        # Verify date range is reflected in report
        with open(result.report_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "2024-01-01" in content or "January 2024" in content

    def test_generate_batch_reports(self, generator):
        """Test generating multiple reports in batch"""
        report_types = [ReportType.SUMMARY, ReportType.ANALYTICS]

        results = generator.generate_batch_reports(report_types)

        assert len(results) == 2
        assert all(result.success for result in results)
        assert results[0].report_type == ReportType.SUMMARY
        assert results[1].report_type == ReportType.ANALYTICS

    def test_error_handling_template_not_found(self, generator):
        """Test error handling when template is not found"""
        with patch.object(generator, '_validate_template_exists', return_value=False):
            result = generator.generate_summary_report()

            assert result.success is False
            assert "template" in result.error.lower()

    def test_error_handling_file_write_error(self, generator):
        """Test error handling for file write errors"""
        # Try to write to invalid path
        invalid_path = "/invalid/path/report.html"

        sections = [ReportSection(title="Test", content="Content")]
        report_data = ReportData(
            report_type=ReportType.SUMMARY,
            title="Test",
            sections=sections
        )

        result = generator._render_html_report(report_data, invalid_path)

        assert result.success is False
        assert result.error is not None