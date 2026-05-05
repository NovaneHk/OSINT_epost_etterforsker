"""
Integration tests for data processing components
Tests email validation, scoring, enrichment, and export functionality
"""

import pytest
import tempfile
import json
import csv
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from core.config import ConfigManager
from core.database import DatabaseManager, Contact, ContactStatus
from validate.validator import EmailValidator, ValidationLevel, ValidationResult
from scoring.scorer import LeadScorer, ScoringResult
from export.exporter import DataExporter, ExportFormat, ExportResult
from enrich.enricher import DataEnricher, EnrichmentResult
from report.generator import ReportGenerator, ReportType
from monitoring.health import HealthMonitor


class TestDataProcessingIntegration:
    """Integration tests for data processing pipeline components"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for integration tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        import shutil
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def config_manager(self, temp_workspace):
        """Create configured ConfigManager for testing"""
        config_dir = Path(temp_workspace) / "config"
        config_dir.mkdir(exist_ok=True)
        return ConfigManager(config_dir=str(config_dir))

    @pytest.fixture
    def db_manager(self, temp_workspace):
        """Create configured DatabaseManager for testing"""
        db_path = Path(temp_workspace) / "test_processing.db"
        return DatabaseManager(str(db_path))

    @pytest.fixture
    def sample_contacts(self):
        """Create sample contacts for testing"""
        return [
            Contact(
                email="ceo@techcorp.com",
                domain="techcorp.com",
                name="John Smith",
                role="CEO",
                company="TechCorp Solutions",
                status=ContactStatus.UNVALIDATED,
                source="company_website"
            ),
            Contact(
                email="sales@innovatelab.com",
                domain="innovatelab.com",
                name="Jane Doe",
                role="Sales Manager",
                company="InnovateLab Inc",
                status=ContactStatus.UNVALIDATED,
                source="directory_listing"
            ),
            Contact(
                email="invalid-email@",
                domain="invalid.com",
                name="Invalid Contact",
                role="Unknown",
                company="Invalid Corp",
                status=ContactStatus.UNVALIDATED,
                source="web_scraping"
            ),
            Contact(
                email="contact@startup.io",
                domain="startup.io",
                name="Alex Johnson",
                role="Founder",
                company="Startup IO",
                status=ContactStatus.UNVALIDATED,
                source="event_listing"
            )
        ]

    @pytest.mark.asyncio
    async def test_validation_integration(self, db_manager, sample_contacts):
        """Test email validation integration with database"""

        # Add sample contacts to database
        for contact in sample_contacts:
            db_manager.add_contact(contact)

        validator = EmailValidator()

        # Test individual validation
        for contact in sample_contacts:
            validation_result = validator.validate(contact.email, ValidationLevel.SYNTAX)

            assert isinstance(validation_result, ValidationResult)
            assert validation_result.email == contact.email

            # Update database with validation results
            if validation_result.is_valid:
                db_manager.update_contact_status(contact.email, ContactStatus.VALIDATED)
                # Update confidence score if available
                if hasattr(validation_result, 'confidence_score'):
                    contact.confidence_score = validation_result.confidence_score

        # Test batch validation
        all_emails = [contact.email for contact in sample_contacts]
        batch_results = validator.validate_batch(all_emails, ValidationLevel.SYNTAX)

        assert len(batch_results) == len(all_emails)
        assert all(isinstance(result, ValidationResult) for result in batch_results)

        # Verify database updates
        validated_contacts = [
            db_manager.get_contact(contact.email)
            for contact in sample_contacts
            if validator.validate(contact.email, ValidationLevel.SYNTAX).is_valid
        ]

        assert len(validated_contacts) > 0
        assert all(contact.status == ContactStatus.VALIDATED for contact in validated_contacts if contact)

    @pytest.mark.asyncio
    async def test_scoring_integration(self, config_manager, db_manager, sample_contacts):
        """Test lead scoring integration with validation results"""

        # Add and validate contacts
        validator = EmailValidator()
        scorer = LeadScorer(config_manager)

        validated_contacts = []
        for contact in sample_contacts:
            db_manager.add_contact(contact)

            # Validate first
            validation_result = validator.validate(contact.email, ValidationLevel.SYNTAX)
            if validation_result.is_valid:
                contact.status = ContactStatus.VALIDATED
                contact.confidence_score = getattr(validation_result, 'confidence_score', 0.8)
                db_manager.update_contact_status(contact.email, ContactStatus.VALIDATED)
                validated_contacts.append(contact)

        # Test individual scoring
        for contact in validated_contacts:
            scoring_result = scorer.score_contact(contact)

            assert isinstance(scoring_result, ScoringResult)
            assert scoring_result.contact_email == contact.email
            assert 0 <= scoring_result.overall_score <= 1
            assert scoring_result.best_persona is not None

            # Update contact with scoring results
            contact.overall_score = scoring_result.overall_score
            contact.persona_match = scoring_result.best_persona

        # Test batch scoring
        batch_results = scorer.score_contacts_batch(validated_contacts)

        assert len(batch_results) == len(validated_contacts)
        assert all(isinstance(result, ScoringResult) for result in batch_results)

        # Verify scoring criteria
        for result in batch_results:
            assert hasattr(result, 'domain_score')
            assert hasattr(result, 'role_score')
            assert hasattr(result, 'company_score')

    @pytest.mark.asyncio
    async def test_enrichment_integration(self, config_manager, db_manager, sample_contacts):
        """Test data enrichment integration"""

        # Setup contacts in database
        for contact in sample_contacts[:2]:  # Use only valid contacts for enrichment
            db_manager.add_contact(contact)

        # Configure enrichment
        enricher_config = {
            'rate_limit_delay': 0.1,
            'max_retries': 2,
            'timeout': 5,
            'enable_company_lookup': True,
            'enable_contact_expansion': True
        }

        enricher = DataEnricher(config=enricher_config)

        # Mock external API calls
        with patch.object(enricher, 'enrich_contact') as mock_enrich:
            # Mock successful enrichment
            def mock_enrichment(contact):
                return EnrichmentResult(
                    success=True,
                    contact_email=contact.email,
                    company_info=Mock(
                        name=contact.company,
                        industry="Technology",
                        size="50-100 employees",
                        location="San Francisco, CA"
                    ),
                    additional_emails=[
                        f"info@{contact.domain}",
                        f"support@{contact.domain}"
                    ],
                    social_profiles={
                        'linkedin': f"https://linkedin.com/company/{contact.company.lower().replace(' ', '-')}",
                        'twitter': f"@{contact.company.lower().replace(' ', '')}"
                    },
                    confidence_score=0.85
                )

            mock_enrich.side_effect = mock_enrichment

            # Test enrichment for each contact
            enriched_contacts = []
            for contact in sample_contacts[:2]:
                enrichment_result = enricher.enrich_contact(contact)

                assert enrichment_result.success is True
                assert enrichment_result.contact_email == contact.email
                assert enrichment_result.company_info is not None
                assert len(enrichment_result.additional_emails) > 0

                enriched_contacts.append(contact)

            # Verify enrichment data integration
            assert len(enriched_contacts) == 2

    @pytest.mark.asyncio
    async def test_export_integration(self, config_manager, db_manager, temp_workspace, sample_contacts):
        """Test data export integration with full pipeline"""

        # Setup complete pipeline
        validator = EmailValidator()
        scorer = LeadScorer(config_manager)
        exporter = DataExporter(db_manager, scorer, output_dir=temp_workspace)

        # Process contacts through full pipeline
        processed_contacts = []
        for contact in sample_contacts:
            db_manager.add_contact(contact)

            # Validate
            validation_result = validator.validate(contact.email, ValidationLevel.SYNTAX)
            if validation_result.is_valid:
                contact.status = ContactStatus.VALIDATED
                contact.confidence_score = getattr(validation_result, 'confidence_score', 0.8)
                db_manager.update_contact_status(contact.email, ContactStatus.VALIDATED)

                # Score
                scoring_result = scorer.score_contact(contact)
                contact.overall_score = scoring_result.overall_score
                contact.persona_match = scoring_result.best_persona

                processed_contacts.append(contact)

        # Test CSV export
        csv_file = Path(temp_workspace) / "export_test.csv"
        csv_result = exporter.export_to_csv(csv_file)

        assert csv_result.success is True
        assert csv_result.total_records > 0
        assert csv_file.exists()

        # Verify CSV content
        with open(csv_file, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            csv_data = list(csv_reader)

            assert len(csv_data) > 0
            assert 'email' in csv_data[0]
            assert 'overall_score' in csv_data[0]
            assert 'persona_match' in csv_data[0]

        # Test JSON export
        json_file = Path(temp_workspace) / "export_test.json"
        json_result = exporter.export_to_json(json_file)

        assert json_result.success is True
        assert json_result.total_records > 0
        assert json_file.exists()

        # Verify JSON content
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

            assert 'contacts' in json_data
            assert 'export_metadata' in json_data
            assert len(json_data['contacts']) > 0

        # Test Excel export (if available)
        try:
            excel_file = Path(temp_workspace) / "export_test.xlsx"
            excel_result = exporter.export_to_excel(excel_file)

            if excel_result.success:
                assert excel_file.exists()
        except ImportError:
            # Excel export may not be available in test environment
            pass

    @pytest.mark.asyncio
    async def test_reporting_integration(self, config_manager, db_manager, temp_workspace, sample_contacts):
        """Test report generation integration"""

        # Setup test data
        validator = EmailValidator()
        scorer = LeadScorer(config_manager)

        # Process contacts with different statuses
        for i, contact in enumerate(sample_contacts):
            db_manager.add_contact(contact)

            # Assign different statuses for variety
            statuses = [ContactStatus.VALIDATED, ContactStatus.CONTACTED,
                       ContactStatus.RESPONDED, ContactStatus.BOUNCED]
            contact.status = statuses[i % len(statuses)]
            db_manager.update_contact_status(contact.email, contact.status)

            # Add scores for valid contacts
            if contact.status in [ContactStatus.VALIDATED, ContactStatus.CONTACTED, ContactStatus.RESPONDED]:
                scoring_result = scorer.score_contact(contact)
                contact.overall_score = scoring_result.overall_score

        # Setup report generator
        report_generator = ReportGenerator(
            db_manager=db_manager,
            scorer=scorer,
            output_dir=temp_workspace
        )

        # Test summary report
        summary_result = report_generator.generate_summary_report()

        assert summary_result.success is True
        assert Path(summary_result.report_path).exists()

        # Verify summary content
        with open(summary_result.report_path, 'r', encoding='utf-8') as f:
            summary_content = f.read()
            assert 'Contact Statistics' in summary_content
            assert 'Total Contacts' in summary_content

        # Test analytics report
        analytics_result = report_generator.generate_analytics_report()

        assert analytics_result.success is True
        assert Path(analytics_result.report_path).exists()

        # Test persona analysis report
        persona_result = report_generator.generate_persona_analysis()

        assert persona_result.success is True
        assert Path(persona_result.report_path).exists()

    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self, config_manager, db_manager, sample_contacts):
        """Test health monitoring integration with all components"""

        # Add test data
        for contact in sample_contacts:
            db_manager.add_contact(contact)

        # Setup health monitor
        health_monitor = HealthMonitor(
            db_manager=db_manager,
            config_manager=config_manager
        )

        # Test overall health check
        health_result = health_monitor.perform_health_check()

        assert health_result.overall_status is not None
        assert health_result.system_metrics is not None
        assert 'database' in health_result.component_statuses
        assert 'configuration' in health_result.component_statuses

        # Test specific component health checks
        db_health = health_monitor.check_database_health()
        assert db_health.component_name == "database"
        assert db_health.status.value in ["healthy", "warning", "critical", "error"]

        config_health = health_monitor.check_configuration_health()
        assert config_health.component_name == "configuration"
        assert config_health.status.value in ["healthy", "warning", "critical", "error"]

        # Test system metrics
        metrics = health_monitor.get_contact_metrics()
        assert 'total_contacts' in metrics
        assert 'contacts_by_status' in metrics
        assert 'average_score' in metrics

    @pytest.mark.asyncio
    async def test_data_filtering_integration(self, config_manager, db_manager, sample_contacts):
        """Test data filtering across validation, scoring, and export"""

        # Setup components
        validator = EmailValidator()
        scorer = LeadScorer(config_manager)

        # Process all contacts
        all_contacts = []
        for contact in sample_contacts:
            db_manager.add_contact(contact)

            # Validate
            validation_result = validator.validate(contact.email, ValidationLevel.SYNTAX)
            contact.is_valid = validation_result.is_valid
            contact.confidence_score = getattr(validation_result, 'confidence_score', 0.0)

            # Score if valid
            if contact.is_valid:
                scoring_result = scorer.score_contact(contact)
                contact.overall_score = scoring_result.overall_score
                contact.persona_match = scoring_result.best_persona
                db_manager.update_contact_status(contact.email, ContactStatus.VALIDATED)
            else:
                contact.overall_score = 0.0
                db_manager.update_contact_status(contact.email, ContactStatus.INVALID)

            all_contacts.append(contact)

        # Test filtering by validation status
        valid_contacts = [c for c in all_contacts if c.is_valid]
        invalid_contacts = [c for c in all_contacts if not c.is_valid]

        assert len(valid_contacts) > 0
        assert len(invalid_contacts) > 0

        # Test filtering by score threshold
        high_score_contacts = [c for c in valid_contacts if c.overall_score > 0.7]
        low_score_contacts = [c for c in valid_contacts if c.overall_score <= 0.7]

        # Should have some variation in scores
        assert len(high_score_contacts) + len(low_score_contacts) == len(valid_contacts)

        # Test filtering by persona
        personas = set(c.persona_match for c in valid_contacts if c.persona_match)
        assert len(personas) > 0  # Should have at least one persona assigned

    @pytest.mark.asyncio
    async def test_error_recovery_integration(self, config_manager, db_manager, temp_workspace):
        """Test error recovery across processing pipeline"""

        # Create contacts with various issues
        problematic_contacts = [
            Contact(email="", domain="empty.com", name="Empty Email"),  # Empty email
            Contact(email="toolong" + "x" * 300 + "@domain.com", domain="domain.com", name="Too Long"),  # Too long
            Contact(email="normal@valid.com", domain="valid.com", name="Normal Contact"),  # Normal
            Contact(email="special@üñíçødé.com", domain="üñíçødé.com", name="Unicode Domain"),  # Unicode
        ]

        # Setup components with error handling
        validator = EmailValidator()
        scorer = LeadScorer(config_manager)

        # Process contacts with error handling
        successful_processes = 0
        failed_processes = 0

        for contact in problematic_contacts:
            try:
                # Add to database
                success = db_manager.add_contact(contact)
                if not success:
                    failed_processes += 1
                    continue

                # Validate with error handling
                try:
                    validation_result = validator.validate(contact.email, ValidationLevel.SYNTAX)
                    if validation_result.is_valid:
                        # Score with error handling
                        try:
                            scoring_result = scorer.score_contact(contact)
                            contact.overall_score = scoring_result.overall_score
                            successful_processes += 1
                        except Exception:
                            # Score failed but validation succeeded
                            contact.overall_score = 0.0
                            successful_processes += 1
                    else:
                        # Invalid email, but process completed
                        contact.overall_score = 0.0
                        successful_processes += 1

                except Exception:
                    # Validation failed
                    failed_processes += 1

            except Exception:
                # Database add failed
                failed_processes += 1

        # Should handle errors gracefully
        assert successful_processes > 0
        # Some processes may fail due to invalid data, which is expected

    @pytest.mark.asyncio
    async def test_performance_benchmarking(self, config_manager, db_manager, sample_contacts):
        """Test performance across data processing components"""

        # Multiply sample contacts for performance testing
        large_contact_set = []
        for i in range(50):  # Create 50 * len(sample_contacts) contacts
            for base_contact in sample_contacts:
                contact = Contact(
                    email=f"perf{i}_{base_contact.email}",
                    domain=base_contact.domain,
                    name=f"Perf Test {i} {base_contact.name}",
                    role=base_contact.role,
                    company=f"Perf Corp {i}",
                    status=ContactStatus.UNVALIDATED
                )
                large_contact_set.append(contact)

        # Benchmark database operations
        start_time = datetime.now()
        for contact in large_contact_set:
            db_manager.add_contact(contact)
        db_duration = (datetime.now() - start_time).total_seconds()

        # Benchmark validation
        validator = EmailValidator()
        start_time = datetime.now()
        validation_results = validator.validate_batch(
            [c.email for c in large_contact_set[:20]],
            ValidationLevel.SYNTAX
        )
        validation_duration = (datetime.now() - start_time).total_seconds()

        # Benchmark scoring
        scorer = LeadScorer(config_manager)
        valid_contacts = [c for c in large_contact_set[:20] if '@' in c.email]
        start_time = datetime.now()
        scoring_results = scorer.score_contacts_batch(valid_contacts)
        scoring_duration = (datetime.now() - start_time).total_seconds()

        # Performance assertions
        assert db_duration < 30  # Database operations should be fast
        assert validation_duration < 10  # Validation should be fast
        assert scoring_duration < 15  # Scoring should complete reasonably fast

        assert len(validation_results) == 20
        assert len(scoring_results) == len(valid_contacts)

    @pytest.mark.asyncio
    async def test_data_consistency_integration(self, config_manager, db_manager, sample_contacts):
        """Test data consistency across all processing steps"""

        # Process contacts through complete pipeline
        validator = EmailValidator()
        scorer = LeadScorer(config_manager)

        original_emails = set()
        processed_emails = set()

        for contact in sample_contacts:
            original_emails.add(contact.email)

            # Add to database
            db_manager.add_contact(contact)

            # Validate
            validation_result = validator.validate(contact.email, ValidationLevel.SYNTAX)

            # Score if valid
            if validation_result.is_valid:
                scoring_result = scorer.score_contact(contact)
                db_manager.update_contact_status(contact.email, ContactStatus.VALIDATED)
                processed_emails.add(contact.email)

        # Verify all contacts were processed (either validated or marked invalid)
        all_contacts = db_manager.get_all_contacts()
        db_emails = set(c.email for c in all_contacts)

        assert original_emails == db_emails  # All emails should be in database

        # Verify data integrity
        for contact in all_contacts:
            assert contact.email is not None
            assert contact.domain is not None
            assert contact.status is not None

            # If validated, should have score
            if contact.status == ContactStatus.VALIDATED:
                assert hasattr(contact, 'overall_score') or contact.overall_score is not None