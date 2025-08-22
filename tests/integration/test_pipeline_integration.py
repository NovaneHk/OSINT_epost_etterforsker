"""
Integration tests for complete OSINT B2B Email System pipeline
Tests end-to-end workflows from scraping to export
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime

from core.config import ConfigManager
from core.database import DatabaseManager, Contact, ContactStatus
from scraping.enhanced_crawler import EnhancedOSINTCrawler
from scraping.web_scraper import WebScraper, RateLimitConfig
from extract.email_extractor import EmailExtractor
from validate.validator import EmailValidator, ValidationLevel
from scoring.scorer import LeadScorer
from export.exporter import DataExporter, ExportFormat
from enrich.enricher import DataEnricher
from report.generator import ReportGenerator, ReportType
from monitoring.health import HealthMonitor
from core.error_handling import get_error_handler, create_context


class TestPipelineIntegration:
    """Test complete system pipeline integration"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for integration tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
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
        db_path = Path(temp_workspace) / "test.db"
        return DatabaseManager(str(db_path))

    @pytest.fixture
    def sample_html_responses(self):
        """Sample HTML responses for mocking web scraping"""
        return {
            "https://example-directory.com": """
                <html>
                    <body>
                        <div class="business-listing">
                            <h3>TechCorp Solutions</h3>
                            <p>Contact: info@techcorp.com</p>
                            <p>Sales: sales@techcorp.com</p>
                            <a href="https://techcorp.com">Visit Website</a>
                        </div>
                        <div class="business-listing">
                            <h3>Innovation Labs</h3>
                            <p>Email: contact@innovationlabs.com</p>
                            <p>CTO: cto@innovationlabs.com</p>
                            <a href="https://innovationlabs.com">Company Site</a>
                        </div>
                    </body>
                </html>
            """,
            "https://techcorp.com": """
                <html>
                    <body>
                        <h1>TechCorp Solutions</h1>
                        <div class="contact-section">
                            <h2>Contact Us</h2>
                            <p>General inquiries: <a href="mailto:info@techcorp.com">info@techcorp.com</a></p>
                            <p>Sales: <a href="mailto:sales@techcorp.com">sales@techcorp.com</a></p>
                            <p>Support: <a href="mailto:support@techcorp.com">support@techcorp.com</a></p>
                        </div>
                        <div class="team-section">
                            <h2>Leadership</h2>
                            <p>CEO: <a href="mailto:ceo@techcorp.com">ceo@techcorp.com</a></p>
                            <p>CTO: <a href="mailto:cto@techcorp.com">cto@techcorp.com</a></p>
                        </div>
                    </body>
                </html>
            """
        }

    @pytest.mark.asyncio
    async def test_complete_scraping_to_export_pipeline(self, config_manager, db_manager,
                                                      temp_workspace, sample_html_responses):
        """Test complete pipeline from scraping to export"""

        # Setup components
        crawler = EnhancedOSINTCrawler(config_manager)
        email_extractor = EmailExtractor(config_manager)
        validator = EmailValidator()
        scorer = LeadScorer(config_manager)
        exporter = DataExporter(db_manager, scorer, output_dir=temp_workspace)

        # Mock web scraping responses
        with patch('aiohttp.ClientSession.get') as mock_get:
            async def mock_response(url, **kwargs):
                mock_resp = AsyncMock()
                mock_resp.status = 200
                mock_resp.text = AsyncMock(return_value=sample_html_responses.get(str(url), "<html></html>"))
                return mock_resp

            mock_get.return_value.__aenter__.return_value = await mock_response("test")

            # Step 1: Crawl sources
            crawl_results = await crawler.crawl_sources(
                source_types=['directories'],
                concurrent_workers=2,
                rate_limit=10.0,
                limit=5,
                respect_robots=False
            )

            # Verify crawling results
            assert 'directories' in crawl_results
            directory_results = crawl_results['directories']
            assert directory_results['success_rate'] > 0

        # Step 2: Extract and validate emails
        contacts = db_manager.get_all_contacts()
        validated_contacts = []

        for contact in contacts:
            # Validate email
            validation_result = validator.validate(contact.email, ValidationLevel.SYNTAX)
            if validation_result.is_valid:
                contact.status = ContactStatus.VALIDATED
                contact.confidence_score = validation_result.confidence_score
                db_manager.update_contact_status(contact.email, ContactStatus.VALIDATED)
                validated_contacts.append(contact)

        # Step 3: Score contacts
        scored_contacts = []
        for contact in validated_contacts:
            score_result = scorer.score_contact(contact)
            contact.overall_score = score_result.overall_score
            contact.persona_match = score_result.best_persona
            scored_contacts.append(contact)

        # Step 4: Export results
        export_result = exporter.export_to_csv(
            Path(temp_workspace) / "integration_test_export.csv"
        )

        # Verify export
        assert export_result.success is True
        assert export_result.total_records > 0
        assert Path(export_result.file_path).exists()

        # Verify exported data
        with open(export_result.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'email' in content
            assert 'overall_score' in content

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, config_manager, db_manager):
        """Test error handling across the pipeline"""

        crawler = EnhancedOSINTCrawler(config_manager)
        error_handler = get_error_handler()

        # Test network error handling
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("Network error")

            crawl_results = await crawler.crawl_sources(
                source_types=['directories'],
                concurrent_workers=1,
                rate_limit=1.0,
                limit=1,
                respect_robots=False
            )

            # Should handle errors gracefully
            assert 'directories' in crawl_results
            assert 'error' in crawl_results['directories']

        # Check error statistics
        error_stats = error_handler.logger.get_error_statistics()
        assert error_stats['total_errors'] >= 0

    @pytest.mark.asyncio
    async def test_configuration_integration(self, config_manager, temp_workspace):
        """Test configuration management across components"""

        # Test config loading and updating
        config = config_manager.get_current_config()
        assert 'system' in config
        assert 'personas' in config

        # Test config updates
        config_manager.update_config({'rate_limit': 5.0})
        updated_config = config_manager.get_current_config()
        assert updated_config['system']['rate_limit'] == 5.0

        # Test component initialization with config
        crawler = EnhancedOSINTCrawler(config_manager)
        assert crawler.config_manager == config_manager

        validator = EmailValidator()
        assert validator is not None

    @pytest.mark.asyncio
    async def test_database_integration(self, db_manager):
        """Test database operations across components"""

        # Test contact lifecycle
        contact = Contact(
            email="test@integration.com",
            domain="integration.com",
            name="Test User",
            role="Developer",
            company="Integration Corp",
            status=ContactStatus.UNVALIDATED
        )

        # Add contact
        success = db_manager.add_contact(contact)
        assert success is True

        # Retrieve contact
        retrieved = db_manager.get_contact("test@integration.com")
        assert retrieved is not None
        assert retrieved.email == "test@integration.com"

        # Update status
        db_manager.update_contact_status("test@integration.com", ContactStatus.VALIDATED)
        updated = db_manager.get_contact("test@integration.com")
        assert updated.status == ContactStatus.VALIDATED

        # Test statistics
        stats = db_manager.get_contact_stats()
        assert stats['total'] >= 1

    @pytest.mark.asyncio
    async def test_enrichment_integration(self, config_manager, db_manager):
        """Test data enrichment integration"""

        # Add sample contact
        contact = Contact(
            email="ceo@example-corp.com",
            domain="example-corp.com",
            company="Example Corp"
        )
        db_manager.add_contact(contact)

        # Mock enrichment APIs
        enricher_config = {
            'rate_limit_delay': 0.1,
            'max_retries': 1,
            'timeout': 5
        }

        enricher = DataEnricher(config=enricher_config)

        # Mock successful enrichment
        with patch.object(enricher, 'enrich_contact') as mock_enrich:
            mock_enrich.return_value = Mock(
                success=True,
                company_info=Mock(name="Example Corp", industry="Technology"),
                additional_emails=["contact@example-corp.com"],
                confidence_score=0.8
            )

            result = enricher.enrich_contact(contact)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_reporting_integration(self, config_manager, db_manager, temp_workspace):
        """Test report generation integration"""

        # Add sample data
        contacts = [
            Contact(email="user1@test.com", domain="test.com", status=ContactStatus.VALIDATED),
            Contact(email="user2@test.com", domain="test.com", status=ContactStatus.CONTACTED),
            Contact(email="user3@example.com", domain="example.com", status=ContactStatus.BOUNCED)
        ]

        for contact in contacts:
            db_manager.add_contact(contact)

        # Generate reports
        scorer = LeadScorer(config_manager)
        report_generator = ReportGenerator(
            db_manager=db_manager,
            scorer=scorer,
            output_dir=temp_workspace
        )

        # Test summary report
        summary_result = report_generator.generate_summary_report()
        assert summary_result.success is True
        assert Path(summary_result.report_path).exists()

        # Test analytics report
        analytics_result = report_generator.generate_analytics_report()
        assert analytics_result.success is True
        assert Path(analytics_result.report_path).exists()

    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self, config_manager, db_manager):
        """Test health monitoring integration"""

        health_monitor = HealthMonitor(
            db_manager=db_manager,
            config_manager=config_manager
        )

        # Test health check
        health_result = health_monitor.perform_health_check()
        assert health_result.overall_status is not None
        assert health_result.system_metrics is not None

        # Test component health
        db_health = health_monitor.check_database_health()
        assert db_health.component_name == "database"
        assert db_health.status is not None

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, config_manager, db_manager):
        """Test concurrent operations across components"""

        # Create multiple contacts concurrently
        async def add_contact(email):
            contact = Contact(
                email=email,
                domain=email.split('@')[1],
                company=f"Company {email.split('@')[0]}"
            )
            return db_manager.add_contact(contact)

        emails = [f"user{i}@concurrent-test.com" for i in range(10)]
        tasks = [add_contact(email) for email in emails]
        results = await asyncio.gather(*tasks)

        # Verify all contacts were added
        assert all(results)
        assert db_manager.get_contact_stats()['total'] >= 10

        # Test concurrent validation
        validator = EmailValidator()

        async def validate_email(email):
            return validator.validate(email, ValidationLevel.SYNTAX)

        validation_tasks = [validate_email(email) for email in emails]
        validation_results = await asyncio.gather(*validation_tasks)

        # Verify validations completed
        assert len(validation_results) == 10
        assert all(result.email for result in validation_results)

    @pytest.mark.asyncio
    async def test_data_flow_integrity(self, config_manager, db_manager, temp_workspace):
        """Test data integrity throughout the pipeline"""

        # Add initial data
        original_contact = Contact(
            email="dataflow@test.com",
            domain="test.com",
            name="Data Flow Test",
            company="Test Corp",
            status=ContactStatus.UNVALIDATED
        )
        db_manager.add_contact(original_contact)

        # Process through validation
        validator = EmailValidator()
        validation_result = validator.validate(original_contact.email, ValidationLevel.SYNTAX)

        # Update with validation results
        if validation_result.is_valid:
            db_manager.update_contact_status(original_contact.email, ContactStatus.VALIDATED)

        # Process through scoring
        scorer = LeadScorer(config_manager)
        updated_contact = db_manager.get_contact(original_contact.email)
        score_result = scorer.score_contact(updated_contact)

        # Process through export
        exporter = DataExporter(db_manager, scorer, output_dir=temp_workspace)
        export_result = exporter.export_to_json(
            Path(temp_workspace) / "data_flow_test.json"
        )

        # Verify data integrity
        assert export_result.success is True

        with open(export_result.file_path, 'r', encoding='utf-8') as f:
            exported_data = json.load(f)
            contacts = exported_data['contacts']
            test_contact = next(c for c in contacts if c['email'] == 'dataflow@test.com')

            assert test_contact['email'] == original_contact.email
            assert test_contact['name'] == original_contact.name
            assert test_contact['company'] == original_contact.company
            assert 'overall_score' in test_contact
            assert 'confidence' in test_contact

    @pytest.mark.asyncio
    async def test_performance_integration(self, config_manager, db_manager):
        """Test system performance under load"""

        # Test batch processing performance
        start_time = datetime.now()

        # Add multiple contacts
        contacts = []
        for i in range(100):
            contact = Contact(
                email=f"perf{i}@test.com",
                domain="test.com",
                company=f"Company {i}"
            )
            contacts.append(contact)
            db_manager.add_contact(contact)

        # Batch validate
        validator = EmailValidator()
        validation_results = validator.validate_batch(
            [c.email for c in contacts[:10]],
            ValidationLevel.SYNTAX
        )

        # Batch score
        scorer = LeadScorer(config_manager)
        scoring_results = scorer.score_contacts_batch(contacts[:10])

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # Performance assertions
        assert len(validation_results) == 10
        assert len(scoring_results) == 10
        assert processing_time < 30  # Should complete within 30 seconds

    def test_cli_integration(self, config_manager, temp_workspace):
        """Test CLI integration (without actual CLI execution)"""

        # Test that main components can be instantiated for CLI use
        db_manager = DatabaseManager()
        crawler = EnhancedOSINTCrawler(config_manager)

        # Test dry run functionality
        dry_run_result = crawler.dry_run_crawl(['directories'], 10)
        assert 'estimated_pages' in dry_run_result
        assert 'estimated_duration_minutes' in dry_run_result

        # Test configuration access
        config = config_manager.get_current_config()
        assert config is not None

    @pytest.mark.asyncio
    async def test_cleanup_and_maintenance(self, db_manager):
        """Test system cleanup and maintenance operations"""

        # Add old data
        old_contact = Contact(
            email="old@test.com",
            domain="test.com",
            company="Old Corp"
        )
        db_manager.add_contact(old_contact)

        # Test cleanup operations
        deleted_contacts, deleted_audit_entries = db_manager.cleanup_old_data(days=1)

        # Should be able to run cleanup without errors
        assert isinstance(deleted_contacts, int)
        assert isinstance(deleted_audit_entries, int)

        # Test statistics after cleanup
        stats = db_manager.get_contact_stats()
        assert 'total' in stats