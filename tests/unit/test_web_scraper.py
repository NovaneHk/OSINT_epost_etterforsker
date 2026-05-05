"""
Unit tests for WebScraper, RobotChecker, ScrapingResult, RateLimitConfig,
CompanyWebsiteScraper (scraping/web_scraper.py)
Brings coverage from 0% toward 80%+
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from urllib.robotparser import RobotFileParser

from scraping.web_scraper import (
    ScrapingResult,
    RateLimitConfig,
    RobotChecker,
    WebScraper,
    CompanyWebsiteScraper,
)


# ---------------------------------------------------------------------------
# ScrapingResult dataclass
# ---------------------------------------------------------------------------

class TestScrapingResult:

    def test_defaults_populated_on_init(self):
        result = ScrapingResult(url="https://example.com", success=True)
        assert result.emails == []
        assert result.links == []
        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)

    def test_explicit_values_preserved(self):
        ts = datetime(2025, 1, 1, 12, 0, 0)
        result = ScrapingResult(
            url="https://example.com",
            success=True,
            status_code=200,
            content="<html>test</html>",
            emails=["a@b.com"],
            links=["https://x.com"],
            response_time=1.5,
            timestamp=ts,
        )
        assert result.url == "https://example.com"
        assert result.success is True
        assert result.status_code == 200
        assert result.content == "<html>test</html>"
        assert result.emails == ["a@b.com"]
        assert result.links == ["https://x.com"]
        assert result.response_time == 1.5
        assert result.timestamp == ts

    def test_failed_result(self):
        result = ScrapingResult(url="https://bad.com", success=False, error="Timeout")
        assert result.success is False
        assert result.error == "Timeout"
        assert result.status_code is None
        assert result.content is None

    def test_timestamp_auto_set(self):
        before = datetime.now()
        result = ScrapingResult(url="https://x.com", success=True)
        after = datetime.now()
        assert before <= result.timestamp <= after

    def test_provided_timestamp_not_overwritten(self):
        ts = datetime(2020, 6, 15)
        result = ScrapingResult(url="https://x.com", success=True, timestamp=ts)
        assert result.timestamp == ts


# ---------------------------------------------------------------------------
# RateLimitConfig dataclass
# ---------------------------------------------------------------------------

class TestRateLimitConfig:

    def test_defaults(self):
        cfg = RateLimitConfig()
        assert cfg.requests_per_second == 1.0
        assert cfg.burst_limit == 5
        assert cfg.delay_between_requests == 1.0
        assert cfg.backoff_factor == 2.0
        assert cfg.max_delay == 60.0

    def test_custom_values(self):
        cfg = RateLimitConfig(
            requests_per_second=2.0,
            burst_limit=10,
            delay_between_requests=0.5,
            backoff_factor=3.0,
            max_delay=120.0,
        )
        assert cfg.requests_per_second == 2.0
        assert cfg.burst_limit == 10
        assert cfg.delay_between_requests == 0.5
        assert cfg.backoff_factor == 3.0
        assert cfg.max_delay == 120.0

    def test_zero_requests_per_second(self):
        cfg = RateLimitConfig(requests_per_second=0.0)
        assert cfg.requests_per_second == 0.0


# ---------------------------------------------------------------------------
# RobotChecker
# ---------------------------------------------------------------------------

class TestRobotChecker:

    def test_init_empty_cache(self):
        checker = RobotChecker()
        assert checker.robot_cache == {}
        assert checker.cache_expiry == {}
        assert checker.cache_duration == timedelta(hours=24)

    @patch("scraping.web_scraper.RobotFileParser")
    def test_can_fetch_allowed(self, MockRFP):
        mock_rp = Mock()
        mock_rp.can_fetch.return_value = True
        MockRFP.return_value = mock_rp

        checker = RobotChecker()
        result = checker.can_fetch("https://example.com/page", "*")
        assert result is True

    @patch("scraping.web_scraper.RobotFileParser")
    def test_can_fetch_disallowed(self, MockRFP):
        mock_rp = Mock()
        mock_rp.can_fetch.return_value = False
        MockRFP.return_value = mock_rp

        checker = RobotChecker()
        result = checker.can_fetch("https://example.com/private", "*")
        assert result is False

    @patch("scraping.web_scraper.RobotFileParser")
    def test_cache_used_on_second_call(self, MockRFP):
        mock_rp = Mock()
        mock_rp.can_fetch.return_value = True
        MockRFP.return_value = mock_rp

        checker = RobotChecker()
        checker.can_fetch("https://example.com/page1", "*")
        checker.can_fetch("https://example.com/page2", "*")

        # RobotFileParser should only be instantiated once (cached)
        assert MockRFP.call_count == 1

    @patch("scraping.web_scraper.RobotFileParser")
    def test_stale_cache_refreshed(self, MockRFP):
        mock_rp = Mock()
        mock_rp.can_fetch.return_value = True
        MockRFP.return_value = mock_rp

        checker = RobotChecker()
        # Force cache to be stale
        checker.robot_cache["https://example.com"] = mock_rp
        checker.cache_expiry["https://example.com"] = datetime.now() - timedelta(hours=25)

        checker.can_fetch("https://example.com/page", "*")
        # Should re-fetch: MockRFP called once for the fresh fetch
        assert MockRFP.call_count == 1

    @patch("scraping.web_scraper.RobotFileParser")
    def test_robots_fetch_exception_returns_true(self, MockRFP):
        """If robots.txt is unavailable, default is to allow."""
        mock_rp = Mock()
        mock_rp.read.side_effect = Exception("Network error")
        MockRFP.return_value = mock_rp

        checker = RobotChecker()
        result = checker.can_fetch("https://down.example.com/page", "*")
        assert result is True

    def test_invalid_url_returns_true(self):
        """Malformed URL should not crash and should default to True."""
        checker = RobotChecker()
        result = checker.can_fetch("not-a-url", "*")
        assert result is True


# ---------------------------------------------------------------------------
# WebScraper initialisation
# ---------------------------------------------------------------------------

class TestWebScraperInit:

    def test_default_init(self):
        with patch("scraping.web_scraper.UserAgent"):
            scraper = WebScraper()
        assert scraper.respect_robots is True
        assert scraper.robot_checker is not None
        assert scraper.session is None
        assert scraper.last_request_time == {}
        assert scraper.request_count == {}

    def test_no_robot_checker_when_respect_robots_false(self):
        with patch("scraping.web_scraper.UserAgent"):
            scraper = WebScraper(respect_robots=False)
        assert scraper.robot_checker is None

    def test_custom_rate_config(self):
        cfg = RateLimitConfig(requests_per_second=5.0)
        with patch("scraping.web_scraper.UserAgent"):
            scraper = WebScraper(rate_config=cfg)
        assert scraper.rate_config.requests_per_second == 5.0

    def test_email_patterns_compiled(self):
        with patch("scraping.web_scraper.UserAgent"):
            scraper = WebScraper()
        assert len(scraper.email_patterns) >= 1

    def test_exclude_patterns_compiled(self):
        with patch("scraping.web_scraper.UserAgent"):
            scraper = WebScraper()
        assert len(scraper.exclude_patterns) >= 1


# ---------------------------------------------------------------------------
# WebScraper helper methods (no session required)
# ---------------------------------------------------------------------------

class TestWebScraperHelpers:

    @pytest.fixture
    def scraper(self):
        with patch("scraping.web_scraper.UserAgent") as MockUA:
            MockUA.return_value.random = "TestBot/1.0"
            s = WebScraper()
        return s

    def test_get_user_agent_returns_string(self, scraper):
        agent = scraper._get_user_agent()
        assert isinstance(agent, str)
        assert len(agent) > 0

    def test_get_user_agent_fallback_on_exception(self, scraper):
        from unittest.mock import PropertyMock
        mock_ua = Mock()
        type(mock_ua).random = PropertyMock(side_effect=Exception("ua error"))
        scraper.user_agent_generator = mock_ua
        agent = scraper._get_user_agent()
        assert "Mozilla" in agent

    def test_extract_domain_simple(self, scraper):
        domain = scraper._extract_domain("https://example.com/page")
        assert "example" in domain

    def test_extract_domain_subdomain(self, scraper):
        domain = scraper._extract_domain("https://blog.company.co.uk/post")
        assert "company" in domain

    def test_extract_domain_invalid_url(self, scraper):
        # Should not raise; returns netloc fallback
        domain = scraper._extract_domain("not-a-url")
        assert isinstance(domain, str)

    def test_check_robots_no_checker_returns_true(self, scraper):
        scraper.robot_checker = None
        assert scraper._check_robots_permission("https://example.com", "*") is True

    def test_check_robots_respect_false_returns_true(self, scraper):
        scraper.respect_robots = False
        assert scraper._check_robots_permission("https://example.com", "*") is True

    def test_check_robots_delegates_to_checker(self, scraper):
        mock_checker = Mock()
        mock_checker.can_fetch.return_value = False
        scraper.robot_checker = mock_checker
        result = scraper._check_robots_permission("https://example.com/private", "TestBot")
        assert result is False
        mock_checker.can_fetch.assert_called_once_with("https://example.com/private", "TestBot")

    def test_extract_emails_finds_plain_email(self, scraper):
        html = "<p>Contact us at hello@company.com for info</p>"
        emails = scraper._extract_emails(html)
        assert "hello@company.com" in emails

    def test_extract_emails_finds_mailto(self, scraper):
        html = '<a href="mailto:jobs@corp.com">Apply</a>'
        emails = scraper._extract_emails(html)
        assert "jobs@corp.com" in emails

    def test_extract_emails_excludes_noreply(self, scraper):
        html = "<p>noreply@company.com is excluded</p>"
        emails = scraper._extract_emails(html)
        assert "noreply@company.com" not in emails

    def test_extract_emails_excludes_example_com(self, scraper):
        html = "<p>test@example.com should be filtered</p>"
        emails = scraper._extract_emails(html)
        assert "test@example.com" not in emails

    def test_extract_emails_empty_html(self, scraper):
        emails = scraper._extract_emails("")
        assert emails == []

    def test_extract_emails_no_emails(self, scraper):
        html = "<p>No contact information here.</p>"
        emails = scraper._extract_emails(html)
        assert emails == []

    def test_extract_emails_multiple(self, scraper):
        html = "<p>a@foo.com and b@bar.com are valid</p>"
        emails = scraper._extract_emails(html)
        assert "a@foo.com" in emails
        assert "b@bar.com" in emails

    def test_extract_links_finds_absolute(self, scraper):
        html = '<a href="https://linked.com/page">Link</a>'
        links = scraper._extract_links(html, "https://example.com")
        assert "https://linked.com/page" in links

    def test_extract_links_resolves_relative(self, scraper):
        html = '<a href="/about">About</a>'
        links = scraper._extract_links(html, "https://example.com")
        assert "https://example.com/about" in links

    def test_extract_links_filters_unwanted_extensions(self, scraper):
        html = '<a href="/file.pdf">PDF</a><a href="/page.html">Page</a>'
        links = scraper._extract_links(html, "https://example.com")
        # .pdf should be filtered by _is_valid_link
        assert "https://example.com/page.html" in links
        assert "https://example.com/file.pdf" not in links

    def test_extract_links_empty_html(self, scraper):
        links = scraper._extract_links("", "https://example.com")
        assert links == []

    def test_is_valid_link_http(self, scraper):
        assert scraper._is_valid_link("https://example.com/page") is True

    def test_is_valid_link_filters_pdf(self, scraper):
        assert scraper._is_valid_link("https://example.com/report.pdf") is False

    def test_is_valid_link_filters_admin_path(self, scraper):
        assert scraper._is_valid_link("https://example.com/admin/panel") is False

    def test_is_valid_link_non_http(self, scraper):
        assert scraper._is_valid_link("ftp://files.example.com/data") is False

    def test_is_valid_link_empty(self, scraper):
        assert scraper._is_valid_link("") is False


# ---------------------------------------------------------------------------
# WebScraper async session management
# ---------------------------------------------------------------------------

class TestWebScraperSession:

    @pytest.mark.asyncio
    async def test_context_manager_starts_session(self):
        with patch("scraping.web_scraper.UserAgent"), \
             patch("scraping.web_scraper.aiohttp.ClientSession") as MockSession, \
             patch("scraping.web_scraper.aiohttp.TCPConnector"):
            MockSession.return_value = AsyncMock()
            async with WebScraper() as scraper:
                assert scraper.session is not None

    @pytest.mark.asyncio
    async def test_context_manager_closes_session(self):
        with patch("scraping.web_scraper.UserAgent"), \
             patch("scraping.web_scraper.aiohttp.ClientSession") as MockSession, \
             patch("scraping.web_scraper.aiohttp.TCPConnector"):
            mock_session = AsyncMock()
            MockSession.return_value = mock_session
            async with WebScraper() as scraper:
                pass
            mock_session.close.assert_called_once()


# ---------------------------------------------------------------------------
# WebScraper.scrape_url (async)
# ---------------------------------------------------------------------------

class TestWebScraperScrapeUrl:

    @pytest.fixture
    def scraper(self):
        with patch("scraping.web_scraper.UserAgent"):
            s = WebScraper(respect_robots=False)
        return s

    @pytest.mark.asyncio
    async def test_scrape_url_success(self, scraper):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="<html><body>hello@corp.com</body></html>")

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=MockAsyncContextManager(mock_response))
        scraper.session = mock_session

        result = await scraper.scrape_url("https://example.com")

        assert result.success is True
        assert result.status_code == 200
        assert "hello@corp.com" in result.emails

    @pytest.mark.asyncio
    async def test_scrape_url_non_200(self, scraper):
        mock_response = AsyncMock()
        mock_response.status = 404

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=MockAsyncContextManager(mock_response))
        scraper.session = mock_session

        result = await scraper.scrape_url("https://example.com/missing")

        assert result.success is False
        assert result.status_code == 404
        assert "404" in result.error

    @pytest.mark.asyncio
    async def test_scrape_url_blocked_by_robots(self, scraper):
        scraper.respect_robots = True
        mock_checker = Mock()
        mock_checker.can_fetch.return_value = False
        scraper.robot_checker = mock_checker

        result = await scraper.scrape_url("https://example.com/private")

        assert result.success is False
        assert "robots" in result.error.lower()

    @pytest.mark.asyncio
    async def test_scrape_url_timeout(self, scraper):
        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())
        scraper.session = mock_session

        result = await scraper.scrape_url("https://slow.com")

        assert result.success is False


# ---------------------------------------------------------------------------
# WebScraper.scrape_multiple_urls (async)
# ---------------------------------------------------------------------------

class TestWebScraperMultipleUrls:

    @pytest.fixture
    def scraper(self):
        with patch("scraping.web_scraper.UserAgent"):
            s = WebScraper(respect_robots=False)
        return s

    @pytest.mark.asyncio
    async def test_scrape_multiple_urls_returns_all(self, scraper):
        urls = ["https://a.com", "https://b.com", "https://c.com"]

        async def fake_scrape(url, max_retries=3):
            return ScrapingResult(url=url, success=True)

        scraper.scrape_url = fake_scrape

        results = await scraper.scrape_multiple_urls(urls, max_concurrent=2)

        assert len(results) == 3
        assert all(isinstance(r, ScrapingResult) for r in results)

    @pytest.mark.asyncio
    async def test_scrape_multiple_urls_handles_exception(self, scraper):
        urls = ["https://crash.com"]

        async def failing_scrape(url, max_retries=3):
            raise RuntimeError("Network failure")

        scraper.scrape_url = failing_scrape

        results = await scraper.scrape_multiple_urls(urls, max_concurrent=1)

        assert len(results) == 1
        assert results[0].success is False
        assert "Exception" in results[0].error

    @pytest.mark.asyncio
    async def test_scrape_multiple_respects_semaphore(self, scraper):
        concurrent_count = []
        active = [0]

        async def fake_scrape(url, max_retries=3):
            active[0] += 1
            concurrent_count.append(active[0])
            await asyncio.sleep(0)
            active[0] -= 1
            return ScrapingResult(url=url, success=True)

        scraper.scrape_url = fake_scrape
        urls = [f"https://site{i}.com" for i in range(5)]

        await scraper.scrape_multiple_urls(urls, max_concurrent=2)

        assert max(concurrent_count) <= 2


# ---------------------------------------------------------------------------
# CompanyWebsiteScraper
# ---------------------------------------------------------------------------

class TestCompanyWebsiteScraper:

    @pytest.fixture
    def company_scraper(self):
        with patch("scraping.web_scraper.UserAgent"):
            web = WebScraper(respect_robots=False)
        return CompanyWebsiteScraper(web_scraper=web)

    def test_init_stores_web_scraper(self, company_scraper):
        assert company_scraper.web_scraper is not None

    def test_target_paths_defined(self, company_scraper):
        assert "/" in company_scraper.target_paths
        assert "/contact" in company_scraper.target_paths
        assert "/about" in company_scraper.target_paths

    @pytest.mark.asyncio
    async def test_scrape_company_domain_with_scheme(self, company_scraper):
        results_store = []

        async def fake_scrape_multiple(urls, **kwargs):
            results_store.extend(urls)
            return [ScrapingResult(url=u, success=True, emails=[]) for u in urls]

        company_scraper.web_scraper.scrape_multiple_urls = fake_scrape_multiple

        result = await company_scraper.scrape_company_domain("https://techcorp.com", max_pages=3)

        assert isinstance(result, dict)
        assert len(results_store) == 3

    @pytest.mark.asyncio
    async def test_scrape_company_domain_adds_https(self, company_scraper):
        urls_called = []

        async def fake_scrape_multiple(urls, **kwargs):
            urls_called.extend(urls)
            return [ScrapingResult(url=u, success=True, emails=[]) for u in urls]

        company_scraper.web_scraper.scrape_multiple_urls = fake_scrape_multiple

        await company_scraper.scrape_company_domain("corp.com", max_pages=2)

        assert all(u.startswith("https://") for u in urls_called)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MockAsyncContextManager:
    """Utility to mock `async with session.get(url) as resp:`"""

    def __init__(self, response):
        self._response = response

    def __call__(self, *args, **kwargs):
        return self

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *args):
        pass
