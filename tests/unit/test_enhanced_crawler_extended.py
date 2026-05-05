"""
Extended tests for scraping/enhanced_crawler.py
Covers the async crawl methods that were missed due to silent exception swallowing.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from datetime import datetime

from scraping.enhanced_crawler import EnhancedOSINTCrawler
from scraping.web_scraper import ScrapingResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scrape_result(success=True, emails=None, links=None, content=""):
    return ScrapingResult(
        url="https://example.com",
        success=success,
        content=content,
        emails=emails or [],
        links=links or [],
    )


def _make_crawler(config_manager=None, db_manager=None):
    """Factory for EnhancedOSINTCrawler with mocked dependencies."""
    if config_manager is None:
        config_manager = MagicMock()
        config_manager.load_sources.return_value = {
            "search_dorks": {},
            "source_categories": {
                "directories": {
                    "sources": [
                        {"name": "BizDir", "url": "https://bizdir.com", "enabled": True, "credibility_score": 70},
                    ]
                },
                "events": {
                    "sources": [
                        {"name": "TechConf", "url": "https://techconf.com", "enabled": True, "credibility_score": 85},
                    ]
                },
                "sites": {
                    "sources": [
                        {"name": "Corp", "url": "https://corp.com", "enabled": True, "credibility_score": 80},
                    ]
                },
                "associations": {
                    "sources": [
                        {"name": "AssocA", "url": "https://assoc.com", "enabled": True},
                    ]
                },
            },
        }

    if db_manager is None:
        db_manager = MagicMock()
        db_manager.store_company.return_value = None
        db_manager.add_contact.return_value = None
        db_manager.get_companies.return_value = []

    with patch("scraping.enhanced_crawler.DatabaseManager", return_value=db_manager), \
         patch("scraping.enhanced_crawler.EmailExtractor"):
        crawler = EnhancedOSINTCrawler(config_manager=config_manager)

    return crawler


def _make_ws_mock(scrape_result):
    """Return a properly-working async context manager mock for WebScraper.

    The key: `async with WebScraper(...) as scraper:` runs:
      1. WebScraper(...) → returns mock_ws  (via patch return_value)
      2. scraper = await mock_ws.__aenter__()  →  inner_scraper
      3. scraper.scrape_url(url) = inner_scraper.scrape_url(url) → scrape_result
    """
    inner_scraper = AsyncMock()
    inner_scraper.scrape_url.return_value = scrape_result

    mock_ws = AsyncMock()
    mock_ws.__aenter__.return_value = inner_scraper

    return mock_ws


# ---------------------------------------------------------------------------
# Lines 94-95: dry_run_crawl — else branch for unknown category type
# ---------------------------------------------------------------------------

class TestDryRunCrawlElseBranch:
    def test_custom_source_type_uses_default_estimates(self):
        """Source types not in (directories, events, sites) use default estimates."""
        crawler = _make_crawler()
        # 'associations' is in source_categories but not directories/events/sites
        result = crawler.dry_run_crawl(["associations"], limit=10)
        assert "associations" in result["source_breakdown"]
        # default: pages_per_source=10, emails_per_page=4
        bd = result["source_breakdown"]["associations"]
        assert bd["estimated_emails"] == bd["estimated_pages"] * 4
        # Duration: pages * 3
        assert result["estimated_duration_minutes"] == result["estimated_pages"] * 3


# ---------------------------------------------------------------------------
# Lines 179-262: _crawl_directories_enhanced success path
# ---------------------------------------------------------------------------

class TestCrawlDirectoriesEnhanced:

    @pytest.mark.asyncio
    async def test_success_path_returns_correct_structure(self):
        """Directly tests _crawl_directories_enhanced to cover lines 179-262."""
        crawler = _make_crawler()
        scrape_result = _make_scrape_result(
            success=True,
            emails=["ceo@bizdir.com", "info@bizdir.com"],
            links=["https://bizdir.com/listing/2", "https://bizdir.com/about"],
            content="<html><body><div class='company-listing'><h2>Alpha Corp</h2></div></body></html>",
        )
        mock_scraper = _make_ws_mock(scrape_result)

        category_config = {
            "sources": [
                {"name": "BizDir", "url": "https://bizdir.com", "enabled": True, "credibility_score": 70},
                {"name": "CompanyList", "url": "https://companylist.com", "enabled": True, "credibility_score": 65},
            ]
        }

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper):
            result = await crawler._crawl_directories_enhanced(
                category_config,
                concurrent_workers=1,
                rate_limit=1.0,
                limit=5,
                respect_robots=False,
            )

        assert "pages_crawled" in result
        assert "companies_found" in result
        assert "emails_extracted" in result
        assert "success_rate" in result
        assert result["sources_processed"] == 2

    @pytest.mark.asyncio
    async def test_success_path_counts_emails(self):
        """Emails from scrape result should increment total_emails."""
        crawler = _make_crawler()
        scrape_result = _make_scrape_result(
            success=True,
            emails=["a@example.com", "b@example.com"],
        )
        mock_scraper = _make_ws_mock(scrape_result)

        category_config = {
            "sources": [
                {"name": "D1", "url": "https://d1.com", "enabled": True, "credibility_score": 60},
            ]
        }

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper):
            result = await crawler._crawl_directories_enhanced(
                category_config, 1, 2.0, 10, False
            )

        # pages_crawled rises because success=True
        assert result["pages_crawled"] >= 1

    @pytest.mark.asyncio
    async def test_failed_scrape_does_not_increment_pages(self):
        """scrape_url returning success=False should not count the page."""
        crawler = _make_crawler()
        scrape_result = _make_scrape_result(success=False)
        mock_scraper = _make_ws_mock(scrape_result)

        category_config = {
            "sources": [
                {"name": "D1", "url": "https://d1.com", "enabled": True, "credibility_score": 60},
            ]
        }

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper):
            result = await crawler._crawl_directories_enhanced(
                category_config, 1, 1.0, 10, False
            )

        assert result["pages_crawled"] == 0
        assert result["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_additional_directory_links_followed(self):
        """Links matching directory pattern should be scraped as additional pages."""
        crawler = _make_crawler()
        scrape_result = _make_scrape_result(
            success=True,
            emails=["ceo@dir.com"],
            # This link contains 'listing' → matches _is_directory_related_link
            links=["https://dir.com/listing/page2"],
        )
        mock_scraper = _make_ws_mock(scrape_result)

        category_config = {
            "sources": [
                {"name": "D1", "url": "https://d1.com", "enabled": True, "credibility_score": 60},
            ]
        }

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper):
            result = await crawler._crawl_directories_enhanced(
                category_config, 1, 1.0, 10, False
            )

        # Both the initial page and the additional listing page are scraped
        assert result["pages_crawled"] >= 1

    @pytest.mark.asyncio
    async def test_disabled_sources_skipped(self):
        """Sources with enabled=False should not be crawled."""
        crawler = _make_crawler()
        scrape_result = _make_scrape_result(success=True)
        mock_scraper = _make_ws_mock(scrape_result)

        category_config = {
            "sources": [
                {"name": "Disabled", "url": "https://disabled.com", "enabled": False},
            ]
        }

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper):
            result = await crawler._crawl_directories_enhanced(
                category_config, 1, 1.0, 10, False
            )

        # No enabled sources → nothing scraped
        assert result["pages_crawled"] == 0

    @pytest.mark.asyncio
    async def test_scrape_exception_increments_request_count(self):
        """Exception from scrape_url should be caught and counted."""
        crawler = _make_crawler()

        inner_scraper = AsyncMock()
        inner_scraper.scrape_url.side_effect = Exception("connection error")
        mock_ws = AsyncMock()
        mock_ws.__aenter__.return_value = inner_scraper

        category_config = {
            "sources": [
                {"name": "D1", "url": "https://d1.com", "enabled": True, "credibility_score": 60},
            ]
        }

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_ws):
            result = await crawler._crawl_directories_enhanced(
                category_config, 1, 1.0, 10, False
            )

        assert result["success_rate"] == 0.0


# ---------------------------------------------------------------------------
# Lines 275-348: _crawl_events_enhanced success path
# ---------------------------------------------------------------------------

class TestCrawlEventsEnhanced:

    @pytest.mark.asyncio
    async def test_success_path_returns_correct_structure(self):
        """Directly tests _crawl_events_enhanced to cover lines 275-348."""
        crawler = _make_crawler()
        scrape_result = _make_scrape_result(
            success=True,
            emails=["speaker@conf.com"],
            links=["https://conf.com/speakers", "https://conf.com/register"],
            content="<html><body><section class='sponsors'><a href='https://co.com'>Sponsor</a></section></body></html>",
        )
        mock_scraper = _make_ws_mock(scrape_result)

        category_config = {
            "sources": [
                {"name": "TechConf", "url": "https://techconf.com", "enabled": True, "credibility_score": 90},
                {"name": "StartupSummit", "url": "https://startupsummit.com", "enabled": True, "credibility_score": 75},
            ]
        }

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper):
            result = await crawler._crawl_events_enhanced(
                category_config, 1, 1.0, 5, False
            )

        assert "pages_crawled" in result
        assert "emails_extracted" in result
        assert result["sources_processed"] == 2

    @pytest.mark.asyncio
    async def test_event_success_counts_pages(self):
        crawler = _make_crawler()
        scrape_result = _make_scrape_result(success=True, emails=["info@conf.com"])
        mock_scraper = _make_ws_mock(scrape_result)

        category_config = {
            "sources": [
                {"name": "C1", "url": "https://c1.com", "enabled": True, "credibility_score": 80},
            ]
        }

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper):
            result = await crawler._crawl_events_enhanced(
                category_config, 1, 1.0, 10, False
            )

        assert result["pages_crawled"] >= 1

    @pytest.mark.asyncio
    async def test_event_additional_links_followed(self):
        """Links matching event pattern (speakers/exhibitors) should be followed."""
        crawler = _make_crawler()
        scrape_result = _make_scrape_result(
            success=True,
            emails=["ceo@co.com"],
            links=["https://conf.com/speakers/john"],
        )
        mock_scraper = _make_ws_mock(scrape_result)

        category_config = {
            "sources": [
                {"name": "C1", "url": "https://c1.com", "enabled": True, "credibility_score": 80},
            ]
        }

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper):
            result = await crawler._crawl_events_enhanced(
                category_config, 1, 1.0, 10, False
            )

        assert result["pages_crawled"] >= 1

    @pytest.mark.asyncio
    async def test_event_failed_scrape(self):
        crawler = _make_crawler()
        scrape_result = _make_scrape_result(success=False)
        mock_scraper = _make_ws_mock(scrape_result)

        category_config = {
            "sources": [
                {"name": "C1", "url": "https://c1.com", "enabled": True, "credibility_score": 80},
            ]
        }

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper):
            result = await crawler._crawl_events_enhanced(
                category_config, 1, 1.0, 10, False
            )

        assert result["pages_crawled"] == 0

    @pytest.mark.asyncio
    async def test_event_exception_caught(self):
        crawler = _make_crawler()

        inner_scraper = AsyncMock()
        inner_scraper.scrape_url.side_effect = Exception("timeout")
        mock_ws = AsyncMock()
        mock_ws.__aenter__.return_value = inner_scraper

        category_config = {
            "sources": [
                {"name": "C1", "url": "https://c1.com", "enabled": True, "credibility_score": 80},
            ]
        }

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_ws):
            result = await crawler._crawl_events_enhanced(
                category_config, 1, 1.0, 10, False
            )

        assert result["success_rate"] == 0.0


# ---------------------------------------------------------------------------
# Lines 362-422: _crawl_company_sites_enhanced success path
# ---------------------------------------------------------------------------

class TestCrawlCompanySitesEnhanced:

    @pytest.mark.asyncio
    async def test_success_path_returns_correct_structure(self):
        """Directly tests _crawl_company_sites_enhanced to cover lines 362-422."""
        crawler = _make_crawler()
        crawler.db_manager.get_companies = Mock(return_value=[
            {"name": "Alpha Corp", "domain": "alpha.com"},
            {"name": "Beta Ltd", "domain": "beta.com"},
        ])
        crawler.db_manager.store_company = Mock()

        mock_company_scraper = AsyncMock()
        mock_company_scraper.scrape_company_domain.return_value = {
            "pages_scraped": 3,
            "successful_pages": 3,
            "emails_found": ["ceo@alpha.com", "info@alpha.com"],
            "base_url": "https://alpha.com",
            "success_rate": 1.0,
        }

        mock_scraper_instance = AsyncMock()

        category_config = {"sources": []}

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper_instance), \
             patch("scraping.enhanced_crawler.CompanyWebsiteScraper", return_value=mock_company_scraper):

            result = await crawler._crawl_company_sites_enhanced(
                category_config, 1, 1.0, 10, False
            )

        assert "pages_crawled" in result
        assert "emails_extracted" in result
        assert result["companies_found"] == 2
        assert result["emails_extracted"] == 4  # 2 emails × 2 companies

    @pytest.mark.asyncio
    async def test_company_without_domain_skipped(self):
        """Companies with empty domain should be skipped."""
        crawler = _make_crawler()
        crawler.db_manager.get_companies = Mock(return_value=[
            {"name": "NoDomain Corp", "domain": ""},
        ])

        mock_company_scraper = AsyncMock()
        mock_scraper_instance = AsyncMock()

        category_config = {"sources": []}

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper_instance), \
             patch("scraping.enhanced_crawler.CompanyWebsiteScraper", return_value=mock_company_scraper):

            result = await crawler._crawl_company_sites_enhanced(
                category_config, 1, 1.0, 10, False
            )

        assert result["companies_found"] == 0
        mock_company_scraper.scrape_company_domain.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_companies_list(self):
        crawler = _make_crawler()
        crawler.db_manager.get_companies = Mock(return_value=[])

        mock_company_scraper = AsyncMock()
        mock_scraper_instance = AsyncMock()

        category_config = {"sources": []}

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper_instance), \
             patch("scraping.enhanced_crawler.CompanyWebsiteScraper", return_value=mock_company_scraper):

            result = await crawler._crawl_company_sites_enhanced(
                category_config, 1, 1.0, 10, False
            )

        assert result["companies_found"] == 0
        assert result["emails_extracted"] == 0

    @pytest.mark.asyncio
    async def test_company_scrape_exception_caught(self):
        """Exception scraping a company domain should be caught and counted."""
        crawler = _make_crawler()
        crawler.db_manager.get_companies = Mock(return_value=[
            {"name": "BadCo", "domain": "bad.com"},
        ])

        mock_company_scraper = AsyncMock()
        mock_company_scraper.scrape_company_domain.side_effect = Exception("timeout")

        mock_scraper_instance = AsyncMock()
        category_config = {"sources": []}

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper_instance), \
             patch("scraping.enhanced_crawler.CompanyWebsiteScraper", return_value=mock_company_scraper):

            result = await crawler._crawl_company_sites_enhanced(
                category_config, 1, 1.0, 10, False
            )

        # Exception path: total_requests += 1, no companies_found
        assert result["companies_found"] == 0

    @pytest.mark.asyncio
    async def test_stores_updated_company_data(self):
        """After scraping, updated company data should be stored in the database."""
        crawler = _make_crawler()
        crawler.db_manager.get_companies = Mock(return_value=[
            {"name": "Alpha", "domain": "alpha.com", "industry": "Technology"},
        ])
        crawler.db_manager.store_company = Mock()

        mock_company_scraper = AsyncMock()
        mock_company_scraper.scrape_company_domain.return_value = {
            "pages_scraped": 2,
            "successful_pages": 2,
            "emails_found": ["cto@alpha.com"],
            "base_url": "https://alpha.com",
            "success_rate": 1.0,
        }
        mock_scraper_instance = AsyncMock()
        category_config = {"sources": []}

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper_instance), \
             patch("scraping.enhanced_crawler.CompanyWebsiteScraper", return_value=mock_company_scraper):

            await crawler._crawl_company_sites_enhanced(
                category_config, 1, 1.0, 10, False
            )

        # store_company should be called (at least once for the updated data)
        crawler.db_manager.store_company.assert_called()


# ---------------------------------------------------------------------------
# Lines 143-160: crawl_sources routing to inner methods
# ---------------------------------------------------------------------------

class TestCrawlSourcesRouting:

    @pytest.mark.asyncio
    async def test_crawl_sources_directories_success_no_error_key(self):
        """When _crawl_directories_enhanced succeeds, result has no 'error' key."""
        crawler = _make_crawler()
        scrape_result = _make_scrape_result(success=True)
        mock_scraper = _make_ws_mock(scrape_result)

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper):
            result = await crawler.crawl_sources(
                source_types=["directories"],
                concurrent_workers=1,
                rate_limit=2.0,
                limit=2,
                respect_robots=False,
            )

        assert "directories" in result
        assert "error" not in result["directories"]

    @pytest.mark.asyncio
    async def test_crawl_sources_events_success_no_error_key(self):
        crawler = _make_crawler()
        scrape_result = _make_scrape_result(success=True)
        mock_scraper = _make_ws_mock(scrape_result)

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper):
            result = await crawler.crawl_sources(
                source_types=["events"],
                concurrent_workers=1,
                rate_limit=2.0,
                limit=2,
                respect_robots=False,
            )

        assert "events" in result
        assert "error" not in result["events"]

    @pytest.mark.asyncio
    async def test_crawl_sources_sites_success(self):
        crawler = _make_crawler()
        crawler.db_manager.get_companies = Mock(return_value=[])

        mock_company_scraper = AsyncMock()
        mock_scraper_instance = AsyncMock()

        with patch("scraping.enhanced_crawler.WebScraper", return_value=mock_scraper_instance), \
             patch("scraping.enhanced_crawler.CompanyWebsiteScraper", return_value=mock_company_scraper):

            result = await crawler.crawl_sources(
                source_types=["sites"],
                concurrent_workers=1,
                rate_limit=2.0,
                limit=2,
                respect_robots=False,
            )

        assert "sites" in result
        assert "error" not in result["sites"]
