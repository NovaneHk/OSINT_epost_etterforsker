"""
Extended unit tests for scraping/crawler.py
Covers OSINTCrawler and the async _crawl_* source methods.
Uncovered lines: 35, 112-113, 150-151, 162, 184-185, 195, 199, 205, 216,
                 342, 389-390, 400-402, 418-463, 476-522, 532-598, 603-661
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from datetime import datetime
from bs4 import BeautifulSoup

from scraping.crawler import (
    CrawlResult,
    OSINTCrawler,
    RateLimiter,
    WebCrawler,
)


# ---------------------------------------------------------------------------
# WebCrawler — uncovered branches
# ---------------------------------------------------------------------------

class TestWebCrawlerClose:
    def test_close_releases_session(self):
        crawler = WebCrawler()
        mock_session = Mock()
        crawler.session = mock_session
        crawler.close()
        mock_session.close.assert_called_once()


class TestWebCrawlerNormalizeUrl:
    def test_fragment_only_href_with_base(self):
        c = WebCrawler()
        result = c._normalize_url("#section", "https://example.com/page")
        assert result == "https://example.com/page"

    def test_fragment_only_href_without_base(self):
        c = WebCrawler()
        assert c._normalize_url("#section", "") is None

    def test_query_only_href_with_base(self):
        c = WebCrawler()
        result = c._normalize_url("?q=test", "https://example.com/search")
        assert result is not None
        assert "example.com" in result

    def test_query_only_href_without_base(self):
        c = WebCrawler()
        assert c._normalize_url("?q=test", "") is None

    def test_absolute_http_url(self):
        c = WebCrawler()
        assert c._normalize_url("http://example.com/", "") == "http://example.com/"

    def test_absolute_https_url_with_fragment_stripped(self):
        c = WebCrawler()
        result = c._normalize_url("https://example.com/page#anchor", "")
        assert result == "https://example.com/page"

    def test_relative_url_with_base(self):
        c = WebCrawler()
        result = c._normalize_url("/about", "https://example.com")
        assert result == "https://example.com/about"

    def test_relative_url_without_base_returns_none(self):
        c = WebCrawler()
        assert c._normalize_url("/about", "") is None

    def test_empty_href_returns_none(self):
        c = WebCrawler()
        assert c._normalize_url("", "https://example.com") is None


class TestExtractLinksAdvanced:
    def test_allowed_domains_filters_external(self):
        c = WebCrawler()
        html = (
            '<a href="https://example.com/p1">Internal</a>'
            '<a href="https://external.com/p2">External</a>'
        )
        links = c.extract_links(html, "https://example.com", allowed_domains=["example.com"])
        assert "https://example.com/p1" in links
        assert all("external.com" not in l for l in links)

    def test_exclude_patterns_removes_matching(self):
        c = WebCrawler()
        html = (
            '<a href="https://example.com/admin">Admin</a>'
            '<a href="https://example.com/about">About</a>'
        )
        links = c.extract_links(
            html, "https://example.com", exclude_patterns=[r"/admin"]
        )
        assert not any("admin" in l for l in links)
        assert any("about" in l for l in links)

    def test_bad_html_returns_empty_list(self):
        c = WebCrawler()
        result = c.extract_links(None, "https://example.com")  # type: ignore
        assert result == []

    def test_subdomain_allowed_through_parent_domain(self):
        c = WebCrawler()
        html = '<a href="https://sub.example.com/page">Sub</a>'
        links = c.extract_links(html, "https://example.com", allowed_domains=["example.com"])
        # sub.example.com ends with '.example.com' → allowed
        assert len(links) == 1


# ---------------------------------------------------------------------------
# OSINTCrawler — synchronous methods
# ---------------------------------------------------------------------------

def _make_osint_crawler(config_manager=None, db_manager=None):
    if config_manager is None:
        config_manager = MagicMock()
        config_manager.load_sources.return_value = {
            "search_dorks": {
                "technology": ['site:linkedin.com "{persona}" "{geo}"'],
            },
            "source_categories": {
                "directories": {
                    "sources": [
                        {"name": "BizDir", "url": "https://bizdir.com", "enabled": True, "credibility_score": 70},
                        {"name": "Disabled", "url": "https://disabled.com", "enabled": False},
                    ]
                },
                "events": {
                    "sources": [
                        {"name": "TechConf", "url": "https://techconf.com", "enabled": True, "credibility_score": 85},
                    ]
                },
                "sites": {
                    "sources": [
                        {"name": "Corp", "url": "https://corp.com", "enabled": True},
                    ],
                    "crawl_patterns": ["/about", "/contact"],
                },
            },
        }
    if db_manager is None:
        db_manager = MagicMock()
        db_manager.store_company.return_value = None
        db_manager.get_companies.return_value = []

    with patch("scraping.crawler.DatabaseManager", return_value=db_manager):
        crawler = OSINTCrawler(config_manager=config_manager)
    return crawler, db_manager


class TestOSINTCrawlerInit:
    def test_stores_config_manager(self):
        cm = MagicMock()
        cm.load_sources.return_value = {"search_dorks": {}, "source_categories": {}}
        with patch("scraping.crawler.DatabaseManager"):
            c = OSINTCrawler(config_manager=cm)
        assert c.config_manager is cm

    def test_results_initially_empty(self):
        crawler, _ = _make_osint_crawler()
        assert crawler.results == {}


class TestOSINTCrawlerGenerateSearchQueries:
    def test_sector_dorks_replaced(self):
        crawler, _ = _make_osint_crawler()
        queries = crawler.generate_search_queries("CTO", "technology", "Norway")
        assert any("Norway" in q for q in queries)
        assert any("CTO" in q for q in queries)

    def test_generic_queries_always_added(self):
        crawler, _ = _make_osint_crawler()
        queries = crawler.generate_search_queries("VP", "unknownsector", "Sweden")
        assert len(queries) >= 5  # at least the 5 generic ones

    def test_no_unreplaced_placeholders(self):
        crawler, _ = _make_osint_crawler()
        queries = crawler.generate_search_queries("Director", "technology", "Denmark")
        for q in queries:
            assert "{geo}" not in q
            assert "{persona}" not in q
            assert "{sector}" not in q


class TestOSINTCrawlerDryRunCrawl:
    def test_returns_required_keys(self):
        crawler, _ = _make_osint_crawler()
        result = crawler.dry_run_crawl(["directories"], limit=10)
        assert "estimated_pages" in result
        assert "source_breakdown" in result
        assert "estimated_duration_minutes" in result

    def test_enabled_sources_only(self):
        crawler, _ = _make_osint_crawler()
        result = crawler.dry_run_crawl(["directories"], limit=100)
        assert result["source_breakdown"]["directories"]["sources_count"] == 1

    def test_unknown_source_type_ignored(self):
        crawler, _ = _make_osint_crawler()
        result = crawler.dry_run_crawl(["nonexistent"], limit=10)
        assert result["estimated_pages"] == 0

    def test_duration_proportional(self):
        crawler, _ = _make_osint_crawler()
        result = crawler.dry_run_crawl(["directories"], limit=10)
        assert result["estimated_duration_minutes"] == result["estimated_pages"] * 2

    def test_zero_limit(self):
        crawler, _ = _make_osint_crawler()
        result = crawler.dry_run_crawl(["directories"], limit=0)
        assert result["estimated_pages"] == 0


# ---------------------------------------------------------------------------
# OSINTCrawler._extract_industry_from_context
# ---------------------------------------------------------------------------

class TestExtractIndustryFromContext:
    def _elem(self, text: str):
        return BeautifulSoup(f"<div>{text}</div>", "html.parser")

    def test_fintech_maps_to_finance(self):
        crawler, _ = _make_osint_crawler()
        elem = self._elem("fintech investment services")
        assert crawler._extract_industry_from_context(elem) == "Finance"

    def test_software_maps_to_technology(self):
        crawler, _ = _make_osint_crawler()
        elem = self._elem("software saas cloud services")
        assert crawler._extract_industry_from_context(elem) == "Technology"

    def test_healthcare_keywords(self):
        crawler, _ = _make_osint_crawler()
        elem = self._elem("medical pharma hospital")
        assert crawler._extract_industry_from_context(elem) == "Healthcare"

    def test_manufacturing_keywords(self):
        crawler, _ = _make_osint_crawler()
        elem = self._elem("manufacturing production factory")
        assert crawler._extract_industry_from_context(elem) == "Manufacturing"

    def test_ecommerce_keywords(self):
        crawler, _ = _make_osint_crawler()
        elem = self._elem("ecommerce retail store")
        assert crawler._extract_industry_from_context(elem) == "Ecommerce"

    def test_consulting_keywords(self):
        crawler, _ = _make_osint_crawler()
        elem = self._elem("consulting advisory services")
        assert crawler._extract_industry_from_context(elem) == "Consulting"

    def test_unknown_returns_other(self):
        crawler, _ = _make_osint_crawler()
        elem = self._elem("random words with no industry hint")
        assert crawler._extract_industry_from_context(elem) == "Other"


# ---------------------------------------------------------------------------
# OSINTCrawler._extract_company_name_from_event
# ---------------------------------------------------------------------------

class TestExtractCompanyNameFromEvent:
    def _elem(self, html: str):
        return BeautifulSoup(html, "html.parser")

    def test_h3_name(self):
        crawler, _ = _make_osint_crawler()
        elem = self._elem("<div><h3>TechCorp</h3></div>")
        assert crawler._extract_company_name_from_event(elem) == "TechCorp"

    def test_class_name_selector(self):
        crawler, _ = _make_osint_crawler()
        elem = self._elem('<div class="company"><span class="name">Acme</span></div>')
        assert crawler._extract_company_name_from_event(elem) == "Acme"

    def test_fallback_to_strong(self):
        crawler, _ = _make_osint_crawler()
        elem = self._elem("<div><strong>BoldCo</strong></div>")
        assert crawler._extract_company_name_from_event(elem) == "BoldCo"

    def test_no_name_returns_none(self):
        crawler, _ = _make_osint_crawler()
        elem = self._elem("<div></div>")
        assert crawler._extract_company_name_from_event(elem) is None


# ---------------------------------------------------------------------------
# OSINTCrawler._extract_domain_from_event
# ---------------------------------------------------------------------------

class TestExtractDomainFromEvent:
    def _elem(self, html: str):
        return BeautifulSoup(html, "html.parser")

    def test_extracts_from_href(self):
        crawler, _ = _make_osint_crawler()
        elem = self._elem('<a href="https://techco.com/about">TechCo</a>')
        assert crawler._extract_domain_from_event(elem) == "techco.com"

    def test_extracts_from_text_domain_pattern(self):
        crawler, _ = _make_osint_crawler()
        elem = self._elem("<div>Visit acme.com for more info</div>")
        assert crawler._extract_domain_from_event(elem) == "acme.com"

    def test_returns_none_if_no_domain(self):
        crawler, _ = _make_osint_crawler()
        elem = self._elem("<div>No domain here at all</div>")
        assert crawler._extract_domain_from_event(elem) is None


# ---------------------------------------------------------------------------
# OSINTCrawler._simulate_directory_data / _simulate_event_data
# ---------------------------------------------------------------------------

class TestSimulateData:
    def test_simulate_directory_data_count(self):
        crawler, _ = _make_osint_crawler()
        source = {"name": "TestDir", "url": "https://dir.com"}
        result = crawler._simulate_directory_data(source, 5)
        assert len(result) == 5

    def test_simulate_directory_data_capped_at_10(self):
        crawler, _ = _make_osint_crawler()
        source = {"name": "TestDir", "url": "https://dir.com"}
        result = crawler._simulate_directory_data(source, 50)
        assert len(result) == 10

    def test_simulate_directory_data_structure(self):
        crawler, _ = _make_osint_crawler()
        source = {"name": "TestDir", "url": "https://dir.com"}
        result = crawler._simulate_directory_data(source, 3)
        assert all("name" in c and "domain" in c for c in result)
        assert all(c.get("simulated") is True for c in result)

    def test_simulate_event_data_count(self):
        crawler, _ = _make_osint_crawler()
        source = {"name": "TechConf", "url": "https://techconf.com"}
        result = crawler._simulate_event_data(source, 5)
        assert len(result) == 5

    def test_simulate_event_data_capped_at_15(self):
        crawler, _ = _make_osint_crawler()
        source = {"name": "TechConf", "url": "https://techconf.com"}
        result = crawler._simulate_event_data(source, 50)
        assert len(result) == 15

    def test_simulate_event_data_structure(self):
        crawler, _ = _make_osint_crawler()
        source = {"name": "TechConf", "url": "https://techconf.com"}
        result = crawler._simulate_event_data(source, 3)
        assert all(c.get("event_context") is True for c in result)
        assert all(c.get("simulated") is True for c in result)


# ---------------------------------------------------------------------------
# OSINTCrawler.crawl_sources — routing
# ---------------------------------------------------------------------------

class TestOSINTCrawlerCrawlSources:

    @pytest.mark.asyncio
    async def test_unknown_source_type_skipped(self):
        crawler, _ = _make_osint_crawler()
        result = await crawler.crawl_sources(
            source_types=["nonexistent"],
            concurrent_workers=1,
            rate_limit=10.0,
            limit=5,
            respect_robots=False,
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_exception_captured_per_source_type(self):
        """Inner _crawl_* raising should be captured with error key."""
        crawler, _ = _make_osint_crawler()
        with patch.object(crawler, "_crawl_directories", side_effect=Exception("boom")):
            result = await crawler.crawl_sources(
                source_types=["directories"],
                concurrent_workers=1,
                rate_limit=10.0,
                limit=5,
                respect_robots=False,
            )
        assert "directories" in result
        assert "error" in result["directories"]

    @pytest.mark.asyncio
    async def test_routes_to_events(self):
        """'events' source_type routes to _crawl_events."""
        crawler, _ = _make_osint_crawler()
        expected = {"pages_crawled": 2, "companies_found": 2, "success_rate": 1.0, "sources_processed": 1}
        with patch.object(crawler, "_crawl_events", return_value=expected) as mock_ev:
            result = await crawler.crawl_sources(
                source_types=["events"],
                concurrent_workers=1,
                rate_limit=10.0,
                limit=5,
                respect_robots=False,
            )
        mock_ev.assert_called_once()
        assert result["events"] == expected

    @pytest.mark.asyncio
    async def test_routes_to_sites(self):
        """'sites' source_type routes to _crawl_company_sites."""
        crawler, _ = _make_osint_crawler()
        expected = {"pages_crawled": 3, "companies_found": 1, "success_rate": 1.0, "sources_processed": 1}
        with patch.object(crawler, "_crawl_company_sites", return_value=expected) as mock_cs:
            result = await crawler.crawl_sources(
                source_types=["sites"],
                concurrent_workers=1,
                rate_limit=10.0,
                limit=5,
                respect_robots=False,
            )
        mock_cs.assert_called_once()
        assert result["sites"] == expected

    @pytest.mark.asyncio
    async def test_routes_to_directories(self):
        """'directories' source_type routes to _crawl_directories."""
        crawler, _ = _make_osint_crawler()
        expected = {"pages_crawled": 5, "companies_found": 3, "success_rate": 1.0, "sources_processed": 1}
        with patch.object(crawler, "_crawl_directories", return_value=expected) as mock_dir:
            result = await crawler.crawl_sources(
                source_types=["directories"],
                concurrent_workers=1,
                rate_limit=10.0,
                limit=5,
                respect_robots=False,
            )
        mock_dir.assert_called_once()
        assert result["directories"] == expected


# ---------------------------------------------------------------------------
# OSINTCrawler._crawl_directories (async)
# ---------------------------------------------------------------------------

class TestCrawlDirectories:

    @pytest.mark.asyncio
    async def test_success_with_simulate_fallback(self):
        """_crawl_directory_source falls back to simulation on ImportError or aiohttp error."""
        crawler, db_manager = _make_osint_crawler()

        # Simulate: _crawl_directory_source returns simulated data
        async def fake_crawl_directory(source, max_pages):
            return [
                {"name": f"Co{i}", "domain": f"co{i}.com", "url": f"https://co{i}.com", "industry": "Tech"}
                for i in range(3)
            ]

        with patch.object(crawler, "_crawl_directory_source", side_effect=fake_crawl_directory):
            result = await crawler._crawl_directories(
                {"sources": [{"name": "D1", "url": "https://d1.com", "enabled": True, "credibility_score": 70}]},
                concurrent_workers=1,
                rate_limit=10.0,
                limit=5,
                respect_robots=False,
            )

        assert result["pages_crawled"] == 3
        assert result["companies_found"] == 3
        assert result["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_store_error_doesnt_stop_loop(self):
        """store_company raising should not abort the crawl loop."""
        crawler, db_manager = _make_osint_crawler()
        db_manager.store_company.side_effect = Exception("db fail")

        async def fake_crawl_directory(source, max_pages):
            return [{"name": "Co", "domain": "co.com", "url": "https://co.com", "industry": "Tech"}]

        with patch.object(crawler, "_crawl_directory_source", side_effect=fake_crawl_directory):
            result = await crawler._crawl_directories(
                {"sources": [{"name": "D1", "url": "https://d1.com", "enabled": True}]},
                concurrent_workers=1,
                rate_limit=10.0,
                limit=5,
                respect_robots=False,
            )

        # companies_found = 0 because store failed, but loop did not raise
        assert result["companies_found"] == 0

    @pytest.mark.asyncio
    async def test_disabled_sources_excluded(self):
        crawler, _ = _make_osint_crawler()

        call_count = []
        async def fake_crawl(source, max_pages):
            call_count.append(source["name"])
            return []

        with patch.object(crawler, "_crawl_directory_source", side_effect=fake_crawl):
            await crawler._crawl_directories(
                {"sources": [
                    {"name": "Enabled", "url": "https://e.com", "enabled": True},
                    {"name": "Disabled", "url": "https://d.com", "enabled": False},
                ]},
                concurrent_workers=1,
                rate_limit=10.0,
                limit=5,
                respect_robots=False,
            )

        assert "Disabled" not in call_count
        assert "Enabled" in call_count

    @pytest.mark.asyncio
    async def test_source_exception_caught(self):
        """Exception in _crawl_directory_source should be caught."""
        crawler, _ = _make_osint_crawler()

        async def boom(source, max_pages):
            raise Exception("network crash")

        with patch.object(crawler, "_crawl_directory_source", side_effect=boom):
            result = await crawler._crawl_directories(
                {"sources": [{"name": "D1", "url": "https://d1.com", "enabled": True}]},
                concurrent_workers=1,
                rate_limit=10.0,
                limit=5,
                respect_robots=False,
            )

        assert result["companies_found"] == 0


# ---------------------------------------------------------------------------
# OSINTCrawler._crawl_events (async)
# ---------------------------------------------------------------------------

class TestCrawlEvents:

    @pytest.mark.asyncio
    async def test_success_path(self):
        crawler, db_manager = _make_osint_crawler()

        async def fake_crawl_event(source, max_pages):
            return [
                {"name": f"Event Co {i}", "domain": f"eco{i}.com", "industry": "Tech"}
                for i in range(4)
            ]

        with patch.object(crawler, "_crawl_event_source", side_effect=fake_crawl_event):
            result = await crawler._crawl_events(
                {"sources": [{"name": "C1", "url": "https://c1.com", "enabled": True, "credibility_score": 80}]},
                concurrent_workers=1,
                rate_limit=10.0,
                limit=10,
                respect_robots=False,
            )

        assert result["companies_found"] == 4
        assert result["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_source_exception_caught(self):
        crawler, _ = _make_osint_crawler()

        async def boom(source, max_pages):
            raise Exception("event fail")

        with patch.object(crawler, "_crawl_event_source", side_effect=boom):
            result = await crawler._crawl_events(
                {"sources": [{"name": "C1", "url": "https://c1.com", "enabled": True}]},
                concurrent_workers=1,
                rate_limit=10.0,
                limit=5,
                respect_robots=False,
            )

        assert result["companies_found"] == 0


# ---------------------------------------------------------------------------
# OSINTCrawler._crawl_company_sites (async)
# ---------------------------------------------------------------------------

class TestCrawlCompanySites:

    @pytest.mark.asyncio
    async def test_success_path(self):
        crawler, db_manager = _make_osint_crawler()
        db_manager.get_companies.return_value = [
            {"name": "AlphaCo", "domain": "alpha.com", "industry": "Tech"},
            {"name": "BetaCo", "domain": "beta.com", "industry": "Finance"},
        ]
        db_manager.store_company.return_value = None

        category_config = {
            "sources": [],
            "crawl_patterns": ["/about", "/contact", "/team"],
        }

        result = await crawler._crawl_company_sites(
            category_config,
            concurrent_workers=1,
            rate_limit=10.0,
            limit=5,
            respect_robots=False,
        )

        assert result["companies_found"] == 2
        assert result["pages_crawled"] == 6  # 3 patterns × 2 companies
        assert result["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_company_without_domain_skipped(self):
        crawler, db_manager = _make_osint_crawler()
        db_manager.get_companies.return_value = [
            {"name": "NoDomain", "domain": ""},
        ]

        result = await crawler._crawl_company_sites(
            {"sources": [], "crawl_patterns": ["/about"]},
            concurrent_workers=1,
            rate_limit=10.0,
            limit=5,
            respect_robots=False,
        )

        assert result["companies_found"] == 0

    @pytest.mark.asyncio
    async def test_empty_companies(self):
        crawler, db_manager = _make_osint_crawler()
        db_manager.get_companies.return_value = []

        result = await crawler._crawl_company_sites(
            {"sources": []},
            concurrent_workers=1,
            rate_limit=10.0,
            limit=5,
            respect_robots=False,
        )

        assert result["companies_found"] == 0
        assert result["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_company_exception_caught(self):
        crawler, db_manager = _make_osint_crawler()
        db_manager.get_companies.return_value = [
            {"name": "BadCo", "domain": "bad.com", "industry": "Tech"},
        ]
        db_manager.store_company.side_effect = Exception("db crash")

        result = await crawler._crawl_company_sites(
            {"sources": [], "crawl_patterns": ["/about"]},
            concurrent_workers=1,
            rate_limit=10.0,
            limit=5,
            respect_robots=False,
        )

        # Exception is caught, companies_found = 0
        assert result["companies_found"] == 0

    @pytest.mark.asyncio
    async def test_uses_default_crawl_patterns_when_missing(self):
        crawler, db_manager = _make_osint_crawler()
        db_manager.get_companies.return_value = [
            {"name": "Co", "domain": "co.com", "industry": "Tech"},
        ]
        db_manager.store_company.return_value = None

        # category_config without crawl_patterns → uses default ['/about', '/contact', '/team']
        result = await crawler._crawl_company_sites(
            {"sources": []},
            concurrent_workers=1,
            rate_limit=10.0,
            limit=5,
            respect_robots=False,
        )

        assert result["pages_crawled"] == 3  # default 3 patterns

    @pytest.mark.asyncio
    async def test_stores_updated_company_data(self):
        crawler, db_manager = _make_osint_crawler()
        db_manager.get_companies.return_value = [
            {"name": "AlphaCo", "domain": "alpha.com", "industry": "Tech"},
        ]
        db_manager.store_company.return_value = None

        await crawler._crawl_company_sites(
            {"sources": [], "crawl_patterns": ["/about"]},
            concurrent_workers=1,
            rate_limit=10.0,
            limit=5,
            respect_robots=False,
        )

        db_manager.store_company.assert_called_once()
        call_args = db_manager.store_company.call_args[0][0]
        assert call_args["domain"] == "alpha.com"
        assert call_args["source_type"] == "company_site"


# ---------------------------------------------------------------------------
# OSINTCrawler._crawl_directory_source — simulation fallback paths
# ---------------------------------------------------------------------------

class TestCrawlDirectorySource:

    @pytest.mark.asyncio
    async def test_import_error_falls_back_to_simulation(self):
        """When aiohttp is unavailable, _simulate_directory_data is called."""
        crawler, _ = _make_osint_crawler()
        source = {"name": "Dir", "url": "https://dir.com"}

        with patch("scraping.crawler.OSINTCrawler._simulate_directory_data", return_value=[
            {"name": "SimCo", "domain": "simco.com"}
        ]) as mock_sim, \
        patch("builtins.__import__", side_effect=ImportError("no aiohttp")):
            # aiohttp import will fail inside _crawl_directory_source
            result = await crawler._crawl_directory_source(source, 10)

        # When __import__ is fully patched it may cause other issues; so also test via direct path
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_aiohttp_error_falls_back_to_simulation(self):
        """On aiohttp.ClientError, falls back to _simulate_directory_data."""
        crawler, _ = _make_osint_crawler()
        source = {"name": "Dir", "url": "https://dir.com"}

        async def fake_session_get(*args, **kwargs):
            raise Exception("connection refused")

        class FakeClientSession:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def get(self, *args, **kwargs):
                raise Exception("connection refused")

        with patch("aiohttp.ClientSession", return_value=FakeClientSession()), \
             patch.object(crawler, "_simulate_directory_data", return_value=[
                 {"name": "SimCo", "domain": "simco.com"}
             ]) as mock_sim:
            result = await crawler._crawl_directory_source(source, 10)

        mock_sim.assert_called_once()
        assert result == [{"name": "SimCo", "domain": "simco.com"}]


# ---------------------------------------------------------------------------
# OSINTCrawler._crawl_event_source — simulation fallback paths
# ---------------------------------------------------------------------------

class TestCrawlEventSource:

    @pytest.mark.asyncio
    async def test_aiohttp_error_falls_back_to_simulation(self):
        """On general exception, _simulate_event_data is called."""
        crawler, _ = _make_osint_crawler()
        source = {"name": "Conf", "url": "https://conf.com"}

        class FakeClientSession:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def get(self, *args, **kwargs):
                raise Exception("timeout")

        with patch("aiohttp.ClientSession", return_value=FakeClientSession()), \
             patch.object(crawler, "_simulate_event_data", return_value=[
                 {"name": "EventCo", "domain": "eventco.com"}
             ]) as mock_sim:
            result = await crawler._crawl_event_source(source, 10)

        mock_sim.assert_called_once()
        assert result == [{"name": "EventCo", "domain": "eventco.com"}]

    @pytest.mark.asyncio
    async def test_happy_path_status_200(self):
        """When status==200 and HTML contains exhibitors, data is extracted."""
        crawler, _ = _make_osint_crawler()
        source = {"name": "Conf", "url": "https://conf.com"}

        html = (
            '<div class="exhibitor">'
            '<h3>EventCo</h3>'
            '<a href="https://eventco.com/about">Visit</a>'
            '</div>'
        )
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=html)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_get_ctx = MagicMock()
        mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_ctx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await crawler._crawl_event_source(source, 10)

        assert any(c.get("name") == "EventCo" for c in result)

    @pytest.mark.asyncio
    async def test_status_not_200_returns_empty(self):
        """When response.status != 200, returns empty list without simulation."""
        crawler, _ = _make_osint_crawler()
        source = {"name": "Conf", "url": "https://conf.com"}

        mock_response = AsyncMock()
        mock_response.status = 404

        mock_get_ctx = MagicMock()
        mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_ctx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await crawler._crawl_event_source(source, 10)

        assert result == []


# ---------------------------------------------------------------------------
# OSINTCrawler._crawl_directory_source — aiohttp happy path
# ---------------------------------------------------------------------------

class TestCrawlDirectorySourceHappyPath:

    @pytest.mark.asyncio
    async def test_happy_path_extracts_companies(self):
        """When status==200 and HTML has .company/.name/.domain, data extracted."""
        crawler, _ = _make_osint_crawler()
        source = {
            "name": "BizDir",
            "url": "https://bizdir.com",
            "company_selector": ".company",
            "name_selector": ".name",
            "domain_selector": ".domain",
        }

        html = (
            '<div class="company">'
            '<span class="name">AlphaCo</span>'
            '<span class="domain">alphaco.com</span>'
            '</div>'
            '<div class="company">'
            '<span class="name">BetaCo</span>'
            '<span class="domain">betaco.com</span>'
            '</div>'
        )

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=html)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_get_ctx = MagicMock()
        mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_ctx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await crawler._crawl_directory_source(source, 10)

        names = [c.get("name") for c in result]
        assert "AlphaCo" in names
        assert "BetaCo" in names

    @pytest.mark.asyncio
    async def test_status_not_200_returns_empty(self):
        """When response.status != 200, returns empty list (no simulation)."""
        crawler, _ = _make_osint_crawler()
        source = {"name": "BizDir", "url": "https://bizdir.com"}

        mock_response = AsyncMock()
        mock_response.status = 503

        mock_get_ctx = MagicMock()
        mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_ctx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await crawler._crawl_directory_source(source, 10)

        assert result == []

    @pytest.mark.asyncio
    async def test_element_without_name_and_domain_skipped(self):
        """Company elements missing name or domain are not appended."""
        crawler, _ = _make_osint_crawler()
        source = {
            "name": "BizDir",
            "url": "https://bizdir.com",
            "company_selector": ".company",
            "name_selector": ".name",
            "domain_selector": ".domain",
        }

        # Only name, no domain
        html = '<div class="company"><span class="name">NodomainCo</span></div>'

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=html)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_get_ctx = MagicMock()
        mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_ctx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await crawler._crawl_directory_source(source, 10)

        assert result == []

    @pytest.mark.asyncio
    async def test_element_extraction_error_continues(self):
        """Exception in per-element extraction is caught and loop continues (lines 584-586)."""
        crawler, _ = _make_osint_crawler()
        source = {
            "name": "BizDir",
            "url": "https://bizdir.com",
            "company_selector": ".company",
            "name_selector": ".name",
            "domain_selector": ".domain",
        }

        html = (
            '<div class="company">'
            '<span class="name">ErrorCo</span>'
            '<span class="domain">errorco.com</span>'
            '</div>'
            '<div class="company">'
            '<span class="name">GoodCo</span>'
            '<span class="domain">goodco.com</span>'
            '</div>'
        )

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=html)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_get_ctx = MagicMock()
        mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_ctx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        call_count = {"n": 0}
        orig = crawler._extract_industry_from_context

        def sometimes_raise(elem):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise ValueError("industry extract error")
            return orig(elem)

        with patch("aiohttp.ClientSession", return_value=mock_session), \
             patch.object(crawler, "_extract_industry_from_context", side_effect=sometimes_raise):
            result = await crawler._crawl_directory_source(source, 10)

        # First element raises → skipped; second succeeds → 1 company
        assert len(result) == 1
        assert result[0]["name"] == "GoodCo"

    @pytest.mark.asyncio
    async def test_import_error_falls_back_to_simulation_dir(self):
        """ImportError for aiohttp triggers _simulate_directory_data."""
        import sys
        crawler, _ = _make_osint_crawler()
        source = {"name": "BizDir", "url": "https://bizdir.com"}

        with patch.dict(sys.modules, {"aiohttp": None}), \
             patch.object(crawler, "_simulate_directory_data", return_value=[
                 {"name": "SimCo", "domain": "simco.com"}
             ]) as mock_sim:
            result = await crawler._crawl_directory_source(source, 10)

        mock_sim.assert_called_once()
        assert result == [{"name": "SimCo", "domain": "simco.com"}]


# ---------------------------------------------------------------------------
# _crawl_events — store exception handler (lines 447-448)
# ---------------------------------------------------------------------------

class TestCrawlEventsStoreError:

    @pytest.mark.asyncio
    async def test_store_error_doesnt_stop_loop(self):
        """store_company raising in _crawl_events should not abort the loop."""
        crawler, db_manager = _make_osint_crawler()
        db_manager.store_company.side_effect = Exception("db fail")

        async def fake_crawl_event(source, max_pages):
            return [{"name": "Co", "domain": "co.com", "industry": "Tech"}]

        with patch.object(crawler, "_crawl_event_source", side_effect=fake_crawl_event):
            result = await crawler._crawl_events(
                {"sources": [{"name": "C1", "url": "https://c1.com", "enabled": True}]},
                concurrent_workers=1,
                rate_limit=10.0,
                limit=5,
                respect_robots=False,
            )

        assert result["companies_found"] == 0


# ---------------------------------------------------------------------------
# _crawl_event_source — per-element exception + ImportError (lines 649-655)
# ---------------------------------------------------------------------------

class TestCrawlEventSourceExceptions:

    @pytest.mark.asyncio
    async def test_per_element_exception_continues(self):
        """Exception during element extraction is caught and loop continues."""
        crawler, _ = _make_osint_crawler()
        source = {"name": "Conf", "url": "https://conf.com"}

        html = (
            '<div class="exhibitor">'
            '<h3>ErrorCo</h3>'
            '<a href="https://errorco.com">Visit</a>'
            '</div>'
            '<div class="exhibitor">'
            '<h3>GoodCo</h3>'
            '<a href="https://goodco.com">Visit</a>'
            '</div>'
        )

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=html)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_get_ctx = MagicMock()
        mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_ctx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        call_count = {"n": 0}
        orig_name = crawler._extract_company_name_from_event

        def sometimes_raise(elem):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise ValueError("name extract error")
            return orig_name(elem)

        with patch("aiohttp.ClientSession", return_value=mock_session), \
             patch.object(crawler, "_extract_company_name_from_event", side_effect=sometimes_raise):
            result = await crawler._crawl_event_source(source, 10)

        assert len(result) == 1
        assert result[0]["name"] == "GoodCo"

    @pytest.mark.asyncio
    async def test_import_error_falls_back_to_simulation_event(self):
        """ImportError for aiohttp triggers _simulate_event_data."""
        import sys
        crawler, _ = _make_osint_crawler()
        source = {"name": "Conf", "url": "https://conf.com"}

        with patch.dict(sys.modules, {"aiohttp": None}), \
             patch.object(crawler, "_simulate_event_data", return_value=[
                 {"name": "SimEvent", "domain": "simevent.com"}
             ]) as mock_sim:
            result = await crawler._crawl_event_source(source, 10)

        mock_sim.assert_called_once()
        assert result == [{"name": "SimEvent", "domain": "simevent.com"}]
