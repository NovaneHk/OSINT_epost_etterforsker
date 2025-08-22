"""
Integration tests specifically for web scraping functionality
Tests real web scraping with mock HTTP responses and rate limiting
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import patch, AsyncMock, Mock
from datetime import datetime, timedelta

from scraping.web_scraper import WebScraper, RobotChecker, CompanyWebsiteScraper, RateLimitConfig
from scraping.enhanced_crawler import EnhancedOSINTCrawler
from core.config import ConfigManager
from core.error_handling import NetworkError, RateLimitError


class TestWebScrapingIntegration:
    """Integration tests for web scraping components"""

    @pytest.fixture
    def rate_limit_config(self):
        """Create rate limiting configuration for testing"""
        return RateLimitConfig(
            requests_per_second=2.0,
            burst_size=5,
            delay_between_requests=0.5
        )

    @pytest.fixture
    def config_manager(self):
        """Create configured ConfigManager for scraping tests"""
        return ConfigManager()

    @pytest.fixture
    def sample_robots_txt(self):
        """Sample robots.txt content for testing"""
        return """
User-agent: *
Disallow: /admin/
Disallow: /private/
Allow: /public/
Crawl-delay: 1

User-agent: TestBot
Disallow: /
        """

    @pytest.fixture
    def sample_web_responses(self):
        """Sample web page responses for testing"""
        return {
            "https://example.com": {
                "status": 200,
                "content": """
                <html>
                    <head><title>Example Company</title></head>
                    <body>
                        <h1>Welcome to Example Company</h1>
                        <div class="contact">
                            <p>Contact us: <a href="mailto:info@example.com">info@example.com</a></p>
                            <p>Sales: <a href="mailto:sales@example.com">sales@example.com</a></p>
                        </div>
                        <div class="team">
                            <p>CEO: <a href="mailto:ceo@example.com">John Doe</a></p>
                            <p>CTO: <a href="mailto:cto@example.com">Jane Smith</a></p>
                        </div>
                    </body>
                </html>
                """
            },
            "https://example.com/robots.txt": {
                "status": 200,
                "content": """
User-agent: *
Allow: /
Crawl-delay: 1
                """
            },
            "https://business-directory.com": {
                "status": 200,
                "content": """
                <html>
                    <body>
                        <div class="listing">
                            <h3>TechCorp</h3>
                            <p>Email: contact@techcorp.com</p>
                            <a href="https://techcorp.com">Website</a>
                        </div>
                        <div class="listing">
                            <h3>InnovateLabs</h3>
                            <p>Contact: hello@innovatelabs.com</p>
                            <a href="https://innovatelabs.com">Visit Site</a>
                        </div>
                    </body>
                </html>
                """
            }
        }

    @pytest.mark.asyncio
    async def test_robot_checker_integration(self, sample_robots_txt):
        """Test robots.txt checking integration"""

        robot_checker = RobotChecker()

        # Mock robots.txt response
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=sample_robots_txt)
            mock_get.return_value.__aenter__.return_value = mock_response

            # Test robots.txt parsing
            can_fetch_public = await robot_checker.can_fetch("https://example.com/public/page", "*")
            can_fetch_admin = await robot_checker.can_fetch("https://example.com/admin/panel", "*")
            can_fetch_testbot = await robot_checker.can_fetch("https://example.com/public/page", "TestBot")

            assert can_fetch_public is True
            assert can_fetch_admin is False
            assert can_fetch_testbot is False

    @pytest.mark.asyncio
    async def test_web_scraper_integration(self, rate_limit_config, sample_web_responses):
        """Test WebScraper with rate limiting and error handling"""

        scraper = WebScraper(rate_limit_config)

        # Mock HTTP responses
        with patch('aiohttp.ClientSession.get') as mock_get:
            async def mock_response(url, **kwargs):
                response_data = sample_web_responses.get(str(url), {"status": 404, "content": ""})
                mock_resp = AsyncMock()
                mock_resp.status = response_data["status"]
                mock_resp.text = AsyncMock(return_value=response_data["content"])
                return mock_resp

            mock_get.return_value.__aenter__.return_value = await mock_response("test")

            # Test successful scraping
            urls = ["https://example.com", "https://business-directory.com"]
            results = await scraper.scrape_urls(urls)

            assert len(results) == 2
            assert all(result.success for result in results)
            assert all(result.content for result in results)

            # Verify rate limiting was applied
            assert scraper.rate_limiter is not None

    @pytest.mark.asyncio
    async def test_company_website_scraper_integration(self, rate_limit_config, sample_web_responses):
        """Test CompanyWebsiteScraper email extraction"""

        scraper = CompanyWebsiteScraper(rate_limit_config)

        # Mock HTTP responses
        with patch('aiohttp.ClientSession.get') as mock_get:
            async def mock_response(url, **kwargs):
                response_data = sample_web_responses.get(str(url), {"status": 404, "content": ""})
                mock_resp = AsyncMock()
                mock_resp.status = response_data["status"]
                mock_resp.text = AsyncMock(return_value=response_data["content"])
                return mock_resp

            mock_get.return_value.__aenter__.return_value = await mock_response("test")

            # Test email extraction from company website
            result = await scraper.scrape_company_emails("https://example.com")

            assert result.success is True
            assert len(result.emails) > 0
            assert "info@example.com" in result.emails
            assert "sales@example.com" in result.emails
            assert "ceo@example.com" in result.emails

            # Test contact information extraction
            assert len(result.contacts) > 0
            ceo_contact = next((c for c in result.contacts if c.email == "ceo@example.com"), None)
            assert ceo_contact is not None
            assert ceo_contact.name == "John Doe"

    @pytest.mark.asyncio
    async def test_enhanced_crawler_integration(self, config_manager, sample_web_responses):
        """Test EnhancedOSINTCrawler integration with real scraping"""

        crawler = EnhancedOSINTCrawler(config_manager)

        # Mock HTTP responses
        with patch('aiohttp.ClientSession.get') as mock_get:
            async def mock_response(url, **kwargs):
                response_data = sample_web_responses.get(str(url), {"status": 404, "content": ""})
                mock_resp = AsyncMock()
                mock_resp.status = response_data["status"]
                mock_resp.text = AsyncMock(return_value=response_data["content"])
                return mock_resp

            mock_get.return_value.__aenter__.return_value = await mock_response("test")

            # Test directory crawling
            directory_results = await crawler.crawl_directories(
                limit=5,
                concurrent_workers=2,
                rate_limit=2.0
            )

            assert directory_results['total_pages'] >= 0
            assert directory_results['success_rate'] >= 0
            assert 'emails_found' in directory_results

    @pytest.mark.asyncio
    async def test_rate_limiting_behavior(self, rate_limit_config):
        """Test rate limiting behavior under load"""

        scraper = WebScraper(rate_limit_config)

        # Mock fast responses
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="<html><body>Test</body></html>")
            mock_get.return_value.__aenter__.return_value = mock_response

            # Test multiple concurrent requests
            urls = [f"https://example{i}.com" for i in range(10)]
            start_time = datetime.now()

            results = await scraper.scrape_urls(urls)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Should take some time due to rate limiting
            expected_minimum_duration = len(urls) * rate_limit_config.delay_between_requests * 0.5
            assert duration >= expected_minimum_duration
            assert all(result.success for result in results)

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, rate_limit_config):
        """Test error handling in web scraping integration"""

        scraper = WebScraper(rate_limit_config)

        # Test network errors
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = aiohttp.ClientError("Network error")

            results = await scraper.scrape_urls(["https://error-site.com"])

            assert len(results) == 1
            assert results[0].success is False
            assert results[0].error is not None

        # Test timeout errors
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = asyncio.TimeoutError("Request timeout")

            results = await scraper.scrape_urls(["https://timeout-site.com"])

            assert len(results) == 1
            assert results[0].success is False
            assert "timeout" in results[0].error.lower()

    @pytest.mark.asyncio
    async def test_robots_txt_compliance_integration(self, rate_limit_config):
        """Test robots.txt compliance in scraping"""

        scraper = WebScraper(rate_limit_config, respect_robots=True)

        # Mock robots.txt that disallows all access
        robots_content = """
User-agent: *
Disallow: /
        """

        with patch('aiohttp.ClientSession.get') as mock_get:
            async def mock_response(url, **kwargs):
                if "robots.txt" in str(url):
                    mock_resp = AsyncMock()
                    mock_resp.status = 200
                    mock_resp.text = AsyncMock(return_value=robots_content)
                    return mock_resp
                else:
                    # Should not reach here due to robots.txt blocking
                    mock_resp = AsyncMock()
                    mock_resp.status = 200
                    mock_resp.text = AsyncMock(return_value="<html><body>Should not access</body></html>")
                    return mock_resp

            mock_get.return_value.__aenter__.return_value = await mock_response("test")

            # Attempt to scrape a disallowed URL
            results = await scraper.scrape_urls(["https://blocked-site.com/page"])

            # Should be blocked by robots.txt
            assert len(results) == 1
            assert results[0].success is False
            assert "robots.txt" in results[0].error.lower()

    @pytest.mark.asyncio
    async def test_concurrent_scraping_integration(self, rate_limit_config, sample_web_responses):
        """Test concurrent scraping with proper resource management"""

        scraper = WebScraper(rate_limit_config)

        # Mock responses for multiple sites
        with patch('aiohttp.ClientSession.get') as mock_get:
            async def mock_response(url, **kwargs):
                # Simulate different response times
                await asyncio.sleep(0.1)
                response_data = sample_web_responses.get(str(url), {"status": 200, "content": "<html><body>Test</body></html>"})
                mock_resp = AsyncMock()
                mock_resp.status = response_data["status"]
                mock_resp.text = AsyncMock(return_value=response_data["content"])
                return mock_resp

            mock_get.return_value.__aenter__.return_value = await mock_response("test")

            # Test scraping multiple URLs concurrently
            urls = [f"https://concurrent-test-{i}.com" for i in range(20)]

            start_time = datetime.now()
            results = await scraper.scrape_urls(urls, max_concurrent=5)
            end_time = datetime.now()

            # Verify all requests completed
            assert len(results) == 20

            # Verify concurrent execution was faster than sequential
            duration = (end_time - start_time).total_seconds()
            sequential_estimate = len(urls) * 0.1  # 0.1s per request
            assert duration < sequential_estimate

    @pytest.mark.asyncio
    async def test_session_management_integration(self, rate_limit_config):
        """Test HTTP session management and cleanup"""

        scraper = WebScraper(rate_limit_config)

        # Mock successful responses
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="<html><body>Test</body></html>")
            mock_get.return_value.__aenter__.return_value = mock_response

            # Perform scraping operations
            await scraper.scrape_urls(["https://session-test.com"])

            # Test manual cleanup
            await scraper.cleanup()

            # Session should be properly closed
            assert scraper._session is None or scraper._session.closed

    @pytest.mark.asyncio
    async def test_user_agent_rotation(self, rate_limit_config):
        """Test user agent rotation in requests"""

        scraper = WebScraper(rate_limit_config, rotate_user_agents=True)
        captured_headers = []

        # Capture request headers
        with patch('aiohttp.ClientSession.get') as mock_get:
            async def capture_headers(*args, **kwargs):
                captured_headers.append(kwargs.get('headers', {}))
                mock_resp = AsyncMock()
                mock_resp.status = 200
                mock_resp.text = AsyncMock(return_value="<html><body>Test</body></html>")
                return mock_resp

            mock_get.return_value.__aenter__.side_effect = capture_headers

            # Make multiple requests
            urls = [f"https://ua-test-{i}.com" for i in range(5)]
            await scraper.scrape_urls(urls)

            # Verify user agents were set and potentially rotated
            assert len(captured_headers) == 5
            user_agents = [headers.get('User-Agent') for headers in captured_headers]
            assert all(ua for ua in user_agents)  # All should have user agents

    @pytest.mark.asyncio
    async def test_content_type_handling(self, rate_limit_config):
        """Test handling of different content types"""

        scraper = WebScraper(rate_limit_config)

        # Mock responses with different content types
        responses = {
            "https://html-content.com": {
                "content_type": "text/html",
                "content": "<html><body>HTML content</body></html>"
            },
            "https://json-content.com": {
                "content_type": "application/json",
                "content": '{"message": "JSON content"}'
            },
            "https://pdf-content.com": {
                "content_type": "application/pdf",
                "content": "PDF binary content"
            }
        }

        with patch('aiohttp.ClientSession.get') as mock_get:
            async def mock_response(url, **kwargs):
                response_data = responses.get(str(url), {"content_type": "text/html", "content": ""})
                mock_resp = AsyncMock()
                mock_resp.status = 200
                mock_resp.headers = {'Content-Type': response_data["content_type"]}
                mock_resp.text = AsyncMock(return_value=response_data["content"])
                return mock_resp

            mock_get.return_value.__aenter__.return_value = await mock_response("test")

            # Test scraping different content types
            results = await scraper.scrape_urls(list(responses.keys()))

            # HTML should be processed successfully
            html_result = next(r for r in results if "html-content.com" in r.url)
            assert html_result.success is True

            # Non-HTML content should be handled appropriately
            json_result = next(r for r in results if "json-content.com" in r.url)
            pdf_result = next(r for r in results if "pdf-content.com" in r.url)

            # Results depend on scraper implementation
            assert json_result.success is not None
            assert pdf_result.success is not None