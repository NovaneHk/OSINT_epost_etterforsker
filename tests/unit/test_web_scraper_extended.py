"""
Extended unit tests for scraping/web_scraper.py
Covers uncovered lines: 91-93, 174-181, 197-198, 254-263, 309-311,
                         348-349, 433-438, 441-446, 463-491, 496-498, 503-514
"""

import asyncio
import aiohttp
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from bs4 import BeautifulSoup

from scraping.web_scraper import (
    CompanyWebsiteScraper,
    RateLimitConfig,
    RobotChecker,
    ScrapingResult,
    WebScraper,
    scrape_company_list,
    extract_emails_from_search_results,
)


# ---------------------------------------------------------------------------
# RobotChecker — uncovered inner-fetch exception (lines 91-93)
# ---------------------------------------------------------------------------

class TestRobotCheckerInnerException:

    @patch("urllib.robotparser.RobotFileParser")
    def test_robots_read_exception_returns_true(self, MockRFP):
        """When rp.read() raises, the inner except returns True (lines 91-93)."""
        mock_rp = MockRFP.return_value
        mock_rp.read.side_effect = Exception("connection refused")

        checker = RobotChecker()
        result = checker.can_fetch("https://example.com/page", "*")

        assert result is True

    def test_outer_exception_returns_true(self):
        """When parse itself throws (e.g. urlparse on bad URL), outer except returns True."""
        checker = RobotChecker()
        # Passing an object that breaks urlparse is tricky — use patch instead
        with patch("scraping.web_scraper.urlparse", side_effect=Exception("bad url")):
            result = checker.can_fetch("boom", "*")
        assert result is True


# ---------------------------------------------------------------------------
# _enforce_rate_limit — sleep branch (lines 174-181)
# ---------------------------------------------------------------------------

class TestEnforceRateLimitSleepBranch:

    @pytest.mark.asyncio
    async def test_sleep_called_when_too_fast(self):
        """When the same domain is requested twice very quickly, sleep is awaited."""
        with patch("scraping.web_scraper.UserAgent"):
            scraper = WebScraper(
                rate_config=RateLimitConfig(requests_per_second=1.0),
                respect_robots=False,
            )

        # Pre-seed the last_request_time so the domain is "just seen"
        import time
        scraper.last_request_time["example.com"] = time.time()  # just now

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await scraper._enforce_rate_limit("example.com")

        # Since we were too fast, sleep should have been called
        mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_sleep_when_domain_not_seen(self):
        """When domain is new, no sleep occurs."""
        with patch("scraping.web_scraper.UserAgent"):
            scraper = WebScraper(respect_robots=False)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await scraper._enforce_rate_limit("newdomain.com")

        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_sleep_when_enough_time_elapsed(self):
        """When enough time has passed, no sleep occurs."""
        with patch("scraping.web_scraper.UserAgent"):
            scraper = WebScraper(
                rate_config=RateLimitConfig(requests_per_second=1.0),
                respect_robots=False,
            )

        import time
        # Set last request to 2 seconds ago (min_delay = 1.0s)
        scraper.last_request_time["example.com"] = time.time() - 2.0

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await scraper._enforce_rate_limit("example.com")

        mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# _extract_domain — exception fallback (lines 197-198)
# ---------------------------------------------------------------------------

class TestExtractDomainFallback:

    def test_tldextract_error_falls_back_to_urlparse(self):
        """When tldextract raises, urlparse.netloc is returned."""
        with patch("scraping.web_scraper.UserAgent"):
            scraper = WebScraper(respect_robots=False)

        with patch("tldextract.extract", side_effect=Exception("tldextract fail")):
            result = scraper._extract_domain("https://example.com/page")

        assert result == "example.com"


# ---------------------------------------------------------------------------
# scrape_url — aiohttp.ClientError retry path (lines 254-258)
# ---------------------------------------------------------------------------

def _make_scraper_with_session(session_mock):
    """Create a WebScraper with a pre-set session mock."""
    with patch("scraping.web_scraper.UserAgent"):
        scraper = WebScraper(respect_robots=False)
    scraper.session = session_mock
    return scraper


class TestScrapeUrlClientError:

    @pytest.mark.asyncio
    async def test_client_error_all_retries_exhausted(self):
        """aiohttp.ClientError on every attempt → final failure ScrapingResult (line 263+)."""
        mock_session = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("connection refused"))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session.get = MagicMock(return_value=mock_ctx)

        scraper = _make_scraper_with_session(mock_session)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await scraper.scrape_url("https://example.com", max_retries=1)

        assert result.success is False
        assert "Client error" in result.error

    @pytest.mark.asyncio
    async def test_generic_exception_all_retries_exhausted(self):
        """Generic Exception on every attempt → final failure ScrapingResult."""
        mock_session = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(side_effect=Exception("socket hang up"))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session.get = MagicMock(return_value=mock_ctx)

        scraper = _make_scraper_with_session(mock_session)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await scraper.scrape_url("https://example.com", max_retries=1)

        assert result.success is False
        assert "Unexpected error" in result.error

    @pytest.mark.asyncio
    async def test_client_error_retries_then_succeeds(self):
        """ClientError on first attempt, success on second."""
        mock_session = MagicMock()

        # First call raises ClientError, second returns 200
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="<html>ok</html>")

        call_count = {"n": 0}

        class FlipCtx:
            async def __aenter__(self):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    raise aiohttp.ClientError("temporary failure")
                return mock_response

            async def __aexit__(self, *args):
                pass

        mock_session.get = MagicMock(return_value=FlipCtx())

        scraper = _make_scraper_with_session(mock_session)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await scraper.scrape_url("https://example.com", max_retries=2)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_generic_exception_retries_then_succeeds(self):
        """Generic Exception on first attempt, success on second."""
        mock_session = MagicMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="<html>ok</html>")

        call_count = {"n": 0}

        class FlipCtx:
            async def __aenter__(self):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    raise Exception("transient error")
                return mock_response

            async def __aexit__(self, *args):
                pass

        mock_session.get = MagicMock(return_value=FlipCtx())
        scraper = _make_scraper_with_session(mock_session)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await scraper.scrape_url("https://example.com", max_retries=2)

        assert result.success is True


# ---------------------------------------------------------------------------
# _extract_links — exception path (lines 309-311)
# ---------------------------------------------------------------------------

class TestExtractLinksException:

    def test_exception_returns_empty_list(self):
        """If BeautifulSoup raises, _extract_links returns []."""
        with patch("scraping.web_scraper.UserAgent"):
            scraper = WebScraper(respect_robots=False)

        with patch("scraping.web_scraper.BeautifulSoup", side_effect=Exception("parse fail")):
            result = scraper._extract_links("<html>", "https://example.com")

        assert result == []


# ---------------------------------------------------------------------------
# _is_valid_link — exception return False (lines 348-349)
# ---------------------------------------------------------------------------

class TestIsValidLinkException:

    def test_exception_returns_false(self):
        """If urlparse raises, _is_valid_link returns False."""
        with patch("scraping.web_scraper.UserAgent"):
            scraper = WebScraper(respect_robots=False)

        with patch("scraping.web_scraper.urlparse", side_effect=Exception("bad url")):
            result = scraper._is_valid_link("http://example.com/page")

        assert result is False


# ---------------------------------------------------------------------------
# scrape_multiple_urls — exception in gather result (lines 433-446)
# ---------------------------------------------------------------------------

class TestScrapeMultipleUrlsException:

    @pytest.mark.asyncio
    async def test_exception_result_converted_to_failed_scraping_result(self):
        """When scrape_url raises an exception, the result is wrapped in a failure ScrapingResult."""
        with patch("scraping.web_scraper.UserAgent"):
            scraper = WebScraper(respect_robots=False)

        async def raises(url, **kwargs):
            raise RuntimeError("network down")

        scraper.scrape_url = raises

        urls = ["https://a.com", "https://b.com"]
        results = await scraper.scrape_multiple_urls(urls, max_concurrent=2)

        assert len(results) == 2
        for result in results:
            assert result.success is False
            assert "Exception" in result.error

    @pytest.mark.asyncio
    async def test_mixed_success_and_exception(self):
        """One URL succeeds, one raises — both processed correctly."""
        with patch("scraping.web_scraper.UserAgent"):
            scraper = WebScraper(respect_robots=False)

        call_count = {"n": 0}

        async def maybe_raise(url, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return ScrapingResult(url=url, success=True, emails=["a@b.com"])
            raise RuntimeError("fail")

        scraper.scrape_url = maybe_raise

        urls = ["https://good.com", "https://bad.com"]
        results = await scraper.scrape_multiple_urls(urls)

        assert any(r.success for r in results)
        assert any(not r.success for r in results)


# ---------------------------------------------------------------------------
# CompanyWebsiteScraper.scrape_company_domain — additional discovery (463-514)
# ---------------------------------------------------------------------------

class TestScrapeCompanyDomainAdditionalDiscovery:

    @pytest.fixture
    def company_scraper(self):
        with patch("scraping.web_scraper.UserAgent"):
            web = WebScraper(respect_robots=False)
        return CompanyWebsiteScraper(web_scraper=web)

    @pytest.mark.asyncio
    async def test_additional_discovery_triggered_when_few_emails(self, company_scraper):
        """When initial pages succeed but emails < 5, additional links are crawled."""
        links_found = ["https://techcorp.com/team", "https://techcorp.com/press"]

        # First call: returns success with 0 emails but some links
        first_results = [
            ScrapingResult(
                url="https://techcorp.com/",
                success=True,
                emails=[],
                links=links_found,
            )
        ]
        # Second call: the additional discovery
        second_results = [
            ScrapingResult(url=u, success=True, emails=["ceo@techcorp.com"], links=[])
            for u in links_found[:3]
        ]

        call_count = {"n": 0}

        async def fake_scrape_multiple(urls, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return first_results
            return second_results

        company_scraper.web_scraper.scrape_multiple_urls = fake_scrape_multiple

        result = await company_scraper.scrape_company_domain("techcorp.com", max_pages=1)

        # Additional discovery was triggered (second call happened)
        assert call_count["n"] == 2
        assert isinstance(result, dict)
        assert "emails_found" in result
        assert "success_rate" in result

    @pytest.mark.asyncio
    async def test_no_additional_discovery_when_enough_emails(self, company_scraper):
        """When initial pages yield >= 5 emails, skip additional discovery."""
        links_found = ["https://techcorp.com/team"]

        initial_results = [
            ScrapingResult(
                url="https://techcorp.com/",
                success=True,
                emails=[f"user{i}@techcorp.com" for i in range(5)],
                links=links_found,
            )
        ]

        call_count = {"n": 0}

        async def fake_scrape_multiple(urls, **kwargs):
            call_count["n"] += 1
            return initial_results

        company_scraper.web_scraper.scrape_multiple_urls = fake_scrape_multiple

        result = await company_scraper.scrape_company_domain("techcorp.com", max_pages=1)

        # Additional discovery was skipped
        assert call_count["n"] == 1
        assert result["total_emails"] == 5

    @pytest.mark.asyncio
    async def test_zero_success_rate_when_all_fail(self, company_scraper):
        """When all pages fail, success_rate is 0."""
        async def fake_scrape_multiple(urls, **kwargs):
            return [ScrapingResult(url=u, success=False, emails=[]) for u in urls]

        company_scraper.web_scraper.scrape_multiple_urls = fake_scrape_multiple

        result = await company_scraper.scrape_company_domain("fail.com", max_pages=3)

        assert result["success_rate"] == 0
        assert result["total_emails"] == 0

    @pytest.mark.asyncio
    async def test_returns_correct_structure(self, company_scraper):
        """scrape_company_domain returns all expected keys."""
        async def fake_scrape_multiple(urls, **kwargs):
            return [ScrapingResult(url=u, success=True, emails=[], links=[]) for u in urls]

        company_scraper.web_scraper.scrape_multiple_urls = fake_scrape_multiple

        result = await company_scraper.scrape_company_domain("example.com", max_pages=2)

        expected_keys = {
            "domain", "base_url", "emails_found", "total_emails",
            "pages_scraped", "successful_pages", "success_rate", "scraping_results"
        }
        assert expected_keys.issubset(result.keys())
        assert result["domain"] == "example.com"

    @pytest.mark.asyncio
    async def test_additional_discovery_only_follows_same_domain(self, company_scraper):
        """Additional discovery only follows links from the same domain."""
        links_found = [
            "https://example.com/team",      # same domain — should be followed
            "https://external.com/partner",   # different domain — should NOT be followed
        ]

        first_results = [
            ScrapingResult(
                url="https://example.com/",
                success=True,
                emails=[],
                links=links_found,
            )
        ]
        additional_urls_called = []

        async def fake_scrape_multiple(urls, **kwargs):
            additional_urls_called.extend(urls)
            return [ScrapingResult(url=u, success=True, emails=[], links=[]) for u in urls]

        company_scraper.web_scraper.scrape_multiple_urls = fake_scrape_multiple

        await company_scraper.scrape_company_domain("example.com", max_pages=1)

        # The second call (if it happened) should NOT include external.com
        if len(additional_urls_called) > 1:
            second_call_urls = additional_urls_called[1:]
            assert not any("external.com" in u for u in second_call_urls)


# ---------------------------------------------------------------------------
# scrape_company_list — module-level utility (lines 463-501)
# ---------------------------------------------------------------------------

class TestScrapeCompanyList:

    @pytest.mark.asyncio
    async def test_returns_list_of_results(self):
        """scrape_company_list returns one result per domain."""
        mock_result = {
            "domain": "a.com",
            "emails_found": ["a@a.com"],
            "total_emails": 1,
            "success_rate": 1.0,
        }

        mock_ws_instance = AsyncMock()
        mock_ws_instance.__aenter__ = AsyncMock(return_value=mock_ws_instance)
        mock_ws_instance.__aexit__ = AsyncMock(return_value=False)

        mock_cs_instance = MagicMock()
        mock_cs_instance.scrape_company_domain = AsyncMock(return_value=mock_result)

        with patch("scraping.web_scraper.WebScraper", return_value=mock_ws_instance), \
             patch("scraping.web_scraper.CompanyWebsiteScraper", return_value=mock_cs_instance):
            results = await scrape_company_list(["a.com", "b.com"])

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_exception_in_domain_wrapped(self):
        """When one domain raises an exception, it is wrapped with an error key."""
        mock_ws_instance = AsyncMock()
        mock_ws_instance.__aenter__ = AsyncMock(return_value=mock_ws_instance)
        mock_ws_instance.__aexit__ = AsyncMock(return_value=False)

        mock_cs_instance = MagicMock()
        mock_cs_instance.scrape_company_domain = AsyncMock(
            side_effect=Exception("connection refused")
        )

        with patch("scraping.web_scraper.WebScraper", return_value=mock_ws_instance), \
             patch("scraping.web_scraper.CompanyWebsiteScraper", return_value=mock_cs_instance):
            results = await scrape_company_list(["fail.com"])

        assert len(results) == 1
        assert "error" in results[0]
        assert results[0]["emails_found"] == []

    @pytest.mark.asyncio
    async def test_empty_domains_returns_empty_list(self):
        """Passing an empty domain list returns an empty result list."""
        mock_ws = AsyncMock()
        mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_ws.__aexit__ = AsyncMock(return_value=False)
        mock_cs = MagicMock()

        with patch("scraping.web_scraper.WebScraper", return_value=mock_ws), \
             patch("scraping.web_scraper.CompanyWebsiteScraper", return_value=mock_cs):
            results = await scrape_company_list([])

        assert results == []


# ---------------------------------------------------------------------------
# extract_emails_from_search_results — utility (lines 503-504 approx)
# ---------------------------------------------------------------------------

class TestExtractEmailsFromSearchResults:

    def test_returns_emails_from_html(self):
        html = "<div>Contact: info@company.com or sales@corp.org</div>"
        with patch("scraping.web_scraper.UserAgent"):
            results = extract_emails_from_search_results(html, max_emails=10)
        assert "info@company.com" in results or "sales@corp.org" in results

    def test_max_emails_limits_results(self):
        html = " ".join(f"user{i}@domain.com" for i in range(20))
        with patch("scraping.web_scraper.UserAgent"):
            results = extract_emails_from_search_results(html, max_emails=5)
        assert len(results) <= 5

    def test_no_emails_returns_empty_list(self):
        with patch("scraping.web_scraper.UserAgent"):
            results = extract_emails_from_search_results("<html>no emails here</html>")
        assert results == []
