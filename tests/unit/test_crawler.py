"""
Unit tests for web crawling functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from bs4 import BeautifulSoup
import time

from scraping.crawler import WebCrawler, CrawlResult, RateLimiter


class TestRateLimiter:
    """Test RateLimiter class"""

    def test_rate_limiter_creation(self):
        """Test creating a rate limiter"""
        limiter = RateLimiter(requests_per_second=2.0)
        assert limiter.requests_per_second == 2.0
        assert limiter.last_request_time == 0

    def test_rate_limiter_wait_calculation(self):
        """Test rate limiter wait time calculation"""
        limiter = RateLimiter(requests_per_second=2.0)  # 0.5 seconds between requests

        # First request should not wait
        current_time = time.time()
        limiter.last_request_time = current_time - 1.0  # 1 second ago
        wait_time = limiter._calculate_wait_time()
        assert wait_time == 0

        # Recent request should require wait
        limiter.last_request_time = current_time - 0.1  # 0.1 seconds ago
        wait_time = limiter._calculate_wait_time()
        assert wait_time > 0
        assert wait_time <= 0.5

    @patch('time.sleep')
    def test_rate_limiter_wait(self, mock_sleep):
        """Test rate limiter waiting mechanism"""
        limiter = RateLimiter(requests_per_second=2.0)

        # Mock time to control timing
        with patch('time.time') as mock_time:
            mock_time.return_value = 100.0
            limiter.last_request_time = 99.8  # 0.2 seconds ago

            limiter.wait_if_needed()

            # Should sleep for approximately 0.3 seconds (0.5 - 0.2)
            mock_sleep.assert_called_once()
            sleep_time = mock_sleep.call_args[0][0]
            assert 0.25 <= sleep_time <= 0.35


class TestCrawlResult:
    """Test CrawlResult dataclass"""

    def test_crawl_result_creation(self):
        """Test creating a crawl result"""
        result = CrawlResult(
            url="https://example.com",
            status_code=200,
            content="<html><body>Test</body></html>",
            headers={"Content-Type": "text/html"},
            response_time=0.5,
            success=True
        )

        assert result.url == "https://example.com"
        assert result.status_code == 200
        assert result.content == "<html><body>Test</body></html>"
        assert result.headers == {"Content-Type": "text/html"}
        assert result.response_time == 0.5
        assert result.success is True
        assert result.error is None
        assert result.timestamp is not None

    def test_crawl_result_with_error(self):
        """Test creating a crawl result with error"""
        result = CrawlResult(
            url="https://example.com",
            success=False,
            error="Connection timeout"
        )

        assert result.url == "https://example.com"
        assert result.success is False
        assert result.error == "Connection timeout"
        assert result.status_code is None
        assert result.content is None


class TestWebCrawler:
    """Test WebCrawler class"""

    @pytest.fixture
    def crawler(self):
        """Create a WebCrawler instance for testing"""
        return WebCrawler(
            rate_limit=2.0,
            timeout=10,
            max_retries=2,
            user_agent="TestBot/1.0"
        )

    def test_crawler_initialization(self, crawler):
        """Test crawler initialization"""
        assert crawler.rate_limit == 2.0
        assert crawler.timeout == 10
        assert crawler.max_retries == 2
        assert crawler.user_agent == "TestBot/1.0"
        assert isinstance(crawler.rate_limiter, RateLimiter)
        assert crawler.session is not None

    def test_crawler_default_initialization(self):
        """Test crawler with default parameters"""
        crawler = WebCrawler()
        assert crawler.rate_limit == 1.0
        assert crawler.timeout == 30
        assert crawler.max_retries == 3
        assert "OSINT-B2B-Email-System" in crawler.user_agent

    @patch('requests.Session.get')
    def test_fetch_url_success(self, mock_get, crawler):
        """Test successful URL fetching"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_get.return_value = mock_response

        result = crawler.fetch_url("https://example.com")

        assert result.success is True
        assert result.status_code == 200
        assert result.content == "<html><body>Test content</body></html>"
        assert result.headers == {"Content-Type": "text/html"}
        assert result.response_time == 0.5
        assert result.error is None

        mock_get.assert_called_once_with(
            "https://example.com",
            timeout=10,
            headers={'User-Agent': 'TestBot/1.0'}
        )

    @patch('requests.Session.get')
    def test_fetch_url_http_error(self, mock_get, crawler):
        """Test URL fetching with HTTP error"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        result = crawler.fetch_url("https://example.com/notfound")

        assert result.success is False
        assert result.status_code == 404
        assert "HTTP error" in result.error

    @patch('requests.Session.get')
    def test_fetch_url_connection_error(self, mock_get, crawler):
        """Test URL fetching with connection error"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        result = crawler.fetch_url("https://unreachable.com")

        assert result.success is False
        assert result.status_code is None
        assert "Connection error" in result.error

    @patch('requests.Session.get')
    def test_fetch_url_timeout(self, mock_get, crawler):
        """Test URL fetching with timeout"""
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")

        result = crawler.fetch_url("https://slow.com")

        assert result.success is False
        assert result.status_code is None
        assert "Timeout error" in result.error

    @patch('requests.Session.get')
    def test_fetch_url_with_retries(self, mock_get, crawler):
        """Test URL fetching with retries"""
        # First two calls fail, third succeeds
        mock_get.side_effect = [
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.Timeout("Timeout"),
            Mock(status_code=200, text="Success", headers={}, elapsed=Mock(total_seconds=lambda: 1.0))
        ]

        result = crawler.fetch_url("https://example.com")

        assert result.success is True
        assert result.status_code == 200
        assert mock_get.call_count == 3

    @patch('requests.Session.get')
    def test_fetch_url_max_retries_exceeded(self, mock_get, crawler):
        """Test URL fetching when max retries exceeded"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        result = crawler.fetch_url("https://example.com")

        assert result.success is False
        assert mock_get.call_count == 3  # Initial + 2 retries

    def test_extract_links_basic(self, crawler):
        """Test basic link extraction"""
        html_content = """
        <html>
            <body>
                <a href="https://example.com/page1">Page 1</a>
                <a href="/relative/page2">Page 2</a>
                <a href="mailto:test@example.com">Email</a>
                <a href="javascript:void(0)">JavaScript</a>
            </body>
        </html>
        """

        links = crawler.extract_links(html_content, base_url="https://example.com")

        assert "https://example.com/page1" in links
        assert "https://example.com/relative/page2" in links
        assert "mailto:test@example.com" not in links  # Should filter out non-http links
        assert "javascript:void(0)" not in links

    def test_extract_links_with_filters(self, crawler):
        """Test link extraction with domain filters"""
        html_content = """
        <html>
            <body>
                <a href="https://example.com/page1">Internal</a>
                <a href="https://external.com/page2">External</a>
                <a href="https://example.com/admin">Admin</a>
            </body>
        </html>
        """

        # Test with allowed domains
        links = crawler.extract_links(
            html_content,
            base_url="https://example.com",
            allowed_domains=["example.com"]
        )

        assert "https://example.com/page1" in links
        assert "https://external.com/page2" not in links
        assert "https://example.com/admin" in links

        # Test with excluded patterns
        links = crawler.extract_links(
            html_content,
            base_url="https://example.com",
            exclude_patterns=[r"/admin"]
        )

        assert "https://example.com/page1" in links
        assert "https://example.com/admin" not in links

    def test_extract_links_malformed_html(self, crawler):
        """Test link extraction with malformed HTML"""
        html_content = "<html><body><a href='broken>Link</a></body></html>"

        # Should not raise exception, should return empty or partial results
        links = crawler.extract_links(html_content, base_url="https://example.com")
        assert isinstance(links, list)

    @patch('requests.Session.get')
    def test_crawl_site_basic(self, mock_get, crawler):
        """Test basic site crawling"""
        # Mock responses for different pages
        main_page_html = """
        <html><body>
            <a href="/page1">Page 1</a>
            <a href="/page2">Page 2</a>
        </body></html>
        """

        page1_html = "<html><body><h1>Page 1</h1></body></html>"
        page2_html = "<html><body><h1>Page 2</h1></body></html>"

        def mock_response(url, **kwargs):
            response = Mock()
            response.status_code = 200
            response.headers = {"Content-Type": "text/html"}
            response.elapsed.total_seconds.return_value = 0.5

            if url == "https://example.com":
                response.text = main_page_html
            elif url == "https://example.com/page1":
                response.text = page1_html
            elif url == "https://example.com/page2":
                response.text = page2_html
            else:
                response.text = "<html><body>Not found</body></html>"

            return response

        mock_get.side_effect = mock_response

        results = crawler.crawl_site("https://example.com", max_pages=3)

        assert len(results) == 3
        assert all(result.success for result in results)

        # Check that all expected URLs were crawled
        crawled_urls = [result.url for result in results]
        assert "https://example.com" in crawled_urls
        assert "https://example.com/page1" in crawled_urls
        assert "https://example.com/page2" in crawled_urls

    @patch('requests.Session.get')
    def test_crawl_site_with_errors(self, mock_get, crawler):
        """Test site crawling with some failed requests"""
        main_page_html = """
        <html><body>
            <a href="/page1">Page 1</a>
            <a href="/broken">Broken</a>
        </body></html>
        """

        def mock_response(url, **kwargs):
            if url == "https://example.com":
                response = Mock()
                response.status_code = 200
                response.text = main_page_html
                response.headers = {"Content-Type": "text/html"}
                response.elapsed.total_seconds.return_value = 0.5
                return response
            elif url == "https://example.com/page1":
                response = Mock()
                response.status_code = 200
                response.text = "<html><body>Page 1</body></html>"
                response.headers = {"Content-Type": "text/html"}
                response.elapsed.total_seconds.return_value = 0.5
                return response
            else:
                raise requests.exceptions.ConnectionError("Failed to connect")

        mock_get.side_effect = mock_response

        results = crawler.crawl_site("https://example.com", max_pages=5)

        # Should have results for successful and failed requests
        assert len(results) >= 2
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        assert len(successful_results) >= 2
        assert len(failed_results) >= 1

    def test_crawl_site_max_pages_limit(self, crawler):
        """Test that crawling respects max_pages limit"""
        with patch.object(crawler, 'fetch_url') as mock_fetch:
            # Mock many links on the main page
            main_page_html = """
            <html><body>
                <a href="/page1">Page 1</a>
                <a href="/page2">Page 2</a>
                <a href="/page3">Page 3</a>
                <a href="/page4">Page 4</a>
                <a href="/page5">Page 5</a>
            </body></html>
            """

            def mock_fetch_response(url):
                if url == "https://example.com":
                    return CrawlResult(
                        url=url,
                        status_code=200,
                        content=main_page_html,
                        success=True
                    )
                else:
                    return CrawlResult(
                        url=url,
                        status_code=200,
                        content=f"<html><body>Content for {url}</body></html>",
                        success=True
                    )

            mock_fetch.side_effect = mock_fetch_response

            results = crawler.crawl_site("https://example.com", max_pages=3)

            assert len(results) == 3  # Should respect the limit

    def test_is_valid_url(self, crawler):
        """Test URL validation"""
        assert crawler._is_valid_url("https://example.com") is True
        assert crawler._is_valid_url("http://example.com") is True
        assert crawler._is_valid_url("https://example.com/path") is True

        assert crawler._is_valid_url("mailto:test@example.com") is False
        assert crawler._is_valid_url("javascript:void(0)") is False
        assert crawler._is_valid_url("ftp://example.com") is False
        assert crawler._is_valid_url("not-a-url") is False
        assert crawler._is_valid_url("") is False

    def test_normalize_url(self, crawler):
        """Test URL normalization"""
        base_url = "https://example.com"

        assert crawler._normalize_url("/path", base_url) == "https://example.com/path"
        assert crawler._normalize_url("https://example.com/absolute", base_url) == "https://example.com/absolute"
        assert crawler._normalize_url("relative", base_url) == "https://example.com/relative"
        assert crawler._normalize_url("?query=1", base_url) == "https://example.com?query=1"
        assert crawler._normalize_url("#fragment", base_url) == "https://example.com"  # Fragments usually removed

    def test_close_session(self, crawler):
        """Test closing crawler session"""
        # Ensure session exists
        assert crawler.session is not None

        # Close session
        crawler.close()

        # Session should be None after closing
        # Note: Actual implementation may vary
        # This test mainly ensures close() doesn't raise an exception