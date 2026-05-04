"""
Targeted tests to cover the remaining 9 uncovered lines:
  core/error_handling.py   : lines 266-272 (should_retry inner function)
  scraping/enhanced_crawler.py : lines 232, 326 (inner loop page-limit breaks)
"""
import pytest
import asyncio
import requests
import aiohttp
from unittest.mock import MagicMock, patch, AsyncMock
from contextlib import asynccontextmanager


# ===========================================================================
# core/error_handling.py lines 266-272
#
# should_retry() is the INNER function of rate_limit_retry().
# To cover those lines we need tenacity to actually invoke it, which means
# wrapping a real function with the decorator and calling it so that it raises
# one of the expected exception types.
# ===========================================================================

def _get_actual_should_retry():
    """Extract the real should_retry() function from rate_limit_retry's closure.

    The function is stored as the 'retry' value in the kwargs dict inside
    the tenacity decorator closure.  This lets us call lines 266-272 directly.
    """
    from core.error_handling import RetryManager
    decorator = RetryManager.rate_limit_retry(max_attempts=2)
    # Closure cell 1 holds a dict of tenacity kwargs (stop, wait, retry, ...)
    retry_dict = decorator.__closure__[1].cell_contents
    return retry_dict['retry']   # The actual should_retry defined at lines 266-272


class TestErrorHandlingShouldRetryActual:
    """Directly invoke should_retry() at lines 266-272 via closure extraction."""

    def test_rate_limit_error_returns_true(self):
        """Lines 266-267: isinstance(exc, RateLimitError) → True."""
        from core.error_handling import RateLimitError
        fn = _get_actual_should_retry()
        assert fn(RateLimitError("limited")) is True

    def test_aiohttp_429_returns_true(self):
        """Lines 268-269: aiohttp 429 → True."""
        fn = _get_actual_should_retry()
        err = aiohttp.ClientResponseError(MagicMock(), (), status=429)
        assert fn(err) is True

    def test_aiohttp_503_returns_true(self):
        """Lines 268-269: aiohttp 503 → True."""
        fn = _get_actual_should_retry()
        err = aiohttp.ClientResponseError(MagicMock(), (), status=503)
        assert fn(err) is True

    def test_aiohttp_200_returns_false(self):
        """Lines 268-269: aiohttp 200 → False."""
        fn = _get_actual_should_retry()
        err = aiohttp.ClientResponseError(MagicMock(), (), status=200)
        assert fn(err) is False

    def test_requests_http_error_429_returns_true(self):
        """Lines 270-271: requests.HTTPError 429 → True."""
        fn = _get_actual_should_retry()
        err = requests.HTTPError()
        err.response = MagicMock()
        err.response.status_code = 429
        assert fn(err) is True

    def test_requests_http_error_503_returns_true(self):
        """Lines 270-271: requests.HTTPError 503 → True."""
        fn = _get_actual_should_retry()
        err = requests.HTTPError()
        err.response = MagicMock()
        err.response.status_code = 503
        assert fn(err) is True

    def test_requests_http_error_400_returns_false(self):
        """Lines 270-271: requests.HTTPError 400 → False."""
        fn = _get_actual_should_retry()
        err = requests.HTTPError()
        err.response = MagicMock()
        err.response.status_code = 400
        assert fn(err) is False

    def test_other_exception_returns_false(self):
        """Line 272: fallback → False."""
        fn = _get_actual_should_retry()
        assert fn(ValueError("nope")) is False


# ===========================================================================
# scraping/enhanced_crawler.py lines 232, 326
#
# Both lines are `break` statements inside inner URL loops:
#   - Line 232: for additional_url in additional_urls: if total_pages >= limit: break
#   - Line 326: for event_link in event_related_links: if total_pages >= limit: break
#
# Strategy: Mock WebScraper.__aenter__ to return a mock scraper whose
# scrape_url returns a mock ScrapeResult, then set total_pages >= limit
# by making the first scrape succeed (total_pages increments to 1)
# and limit=1 so the break fires immediately when inner loop starts.
# ===========================================================================

def _make_scrape_result(success=True, emails=None, links=None, content="<html></html>"):
    """Build a mock ScrapeResult-like object."""
    r = MagicMock()
    r.success = success
    r.emails = emails or []
    r.links = links or []
    r.content = content
    return r


def _make_enhanced_crawler_for_crawl():
    from scraping.enhanced_crawler import EnhancedOSINTCrawler
    c = EnhancedOSINTCrawler.__new__(EnhancedOSINTCrawler)
    c.db_manager = MagicMock()
    c.db_manager.store_company = MagicMock()
    c.db_manager.store_email = MagicMock()
    c._store_extracted_email = AsyncMock(return_value=None)
    c._extract_companies_from_directory = AsyncMock(return_value=[])
    c._extract_companies_from_event = AsyncMock(return_value=[])
    return c


@asynccontextmanager
async def _mock_scraper_cm(scrape_result, **_kwargs):
    """Async context manager yielding a mock scraper."""
    mock_scraper = MagicMock()
    mock_scraper.scrape_url = AsyncMock(return_value=scrape_result)
    yield mock_scraper


class TestEnhancedCrawlerInnerLoopBreaks:

    @pytest.mark.asyncio
    async def test_directory_inner_loop_breaks_at_limit(self):
        """Line 232: inner additional_urls loop breaks when total_pages >= limit."""
        c = _make_enhanced_crawler_for_crawl()

        # First call succeeds → total_pages = 1, limit=1 → break fires
        main_result = _make_scrape_result(
            success=True,
            links=["http://example.com/dir1", "http://example.com/dir2"]
        )

        # Ensure _is_directory_related_link returns True for those links
        with patch.object(c, '_is_directory_related_link', return_value=True), \
             patch('scraping.enhanced_crawler.WebScraper',
                   return_value=_mock_scraper_cm(main_result)):
            result = await c._crawl_directories_enhanced(
                category_config={
                    'sources': [{'name': 'TestDir', 'url': 'http://example.com',
                                 'enabled': True}]
                },
                concurrent_workers=1,
                rate_limit=1.0,
                limit=1,           # total_pages (1) >= limit (1) → break
                respect_robots=False,
            )

        assert isinstance(result, dict)
        assert result['pages_crawled'] >= 1

    @pytest.mark.asyncio
    async def test_event_inner_loop_breaks_at_limit(self):
        """Line 326: inner event_related_links loop breaks when total_pages >= limit."""
        c = _make_enhanced_crawler_for_crawl()

        main_result = _make_scrape_result(
            success=True,
            links=["http://event.com/speakers", "http://event.com/exhibitors"]
        )

        with patch.object(c, '_is_event_related_link', return_value=True), \
             patch('scraping.enhanced_crawler.WebScraper',
                   return_value=_mock_scraper_cm(main_result)):
            result = await c._crawl_events_enhanced(
                category_config={
                    'sources': [{'name': 'TestEvent', 'url': 'http://event.com',
                                 'enabled': True}]
                },
                concurrent_workers=1,
                rate_limit=1.0,
                limit=1,           # total_pages (1) >= limit (1) → break
                respect_robots=False,
            )

        assert isinstance(result, dict)
        assert result['pages_crawled'] >= 1
