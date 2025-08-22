"""
Real Web Scraping Implementation
Advanced web scraping with rate limiting, error handling, and robots.txt compliance
"""

import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
import re
import logging
import time
import random
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, parse_qs
from urllib.robotparser import RobotFileParser
import tldextract
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)


@dataclass
class ScrapingResult:
    """Result of a web scraping operation"""
    url: str
    success: bool
    status_code: Optional[int] = None
    content: Optional[str] = None
    emails: List[str] = None
    links: List[str] = None
    error: Optional[str] = None
    response_time: float = 0.0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.emails is None:
            self.emails = []
        if self.links is None:
            self.links = []


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_second: float = 1.0
    burst_limit: int = 5
    delay_between_requests: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 60.0


class RobotChecker:
    """Handles robots.txt compliance checking"""

    def __init__(self):
        self.robot_cache: Dict[str, RobotFileParser] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_duration = timedelta(hours=24)

    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """Check if URL can be fetched according to robots.txt"""
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            robots_url = urljoin(base_url, "/robots.txt")

            # Check cache
            if base_url in self.robot_cache:
                if datetime.now() - self.cache_expiry[base_url] < self.cache_duration:
                    return self.robot_cache[base_url].can_fetch(user_agent, url)

            # Fetch and parse robots.txt
            try:
                rp = RobotFileParser()
                rp.set_url(robots_url)
                rp.read()

                self.robot_cache[base_url] = rp
                self.cache_expiry[base_url] = datetime.now()

                return rp.can_fetch(user_agent, url)
            except Exception as e:
                logger.warning(f"Could not fetch robots.txt for {base_url}: {e}")
                return True  # Allow if robots.txt is unavailable

        except Exception as e:
            logger.error(f"Error checking robots.txt for {url}: {e}")
            return True  # Allow if there's an error


class WebScraper:
    """Advanced web scraper with rate limiting and error handling"""

    def __init__(self, rate_config: RateLimitConfig = None, respect_robots: bool = True):
        self.rate_config = rate_config or RateLimitConfig()
        self.respect_robots = respect_robots
        self.robot_checker = RobotChecker() if respect_robots else None
        self.user_agent_generator = UserAgent()
        self.session = None
        self.last_request_time = {}
        self.request_count = {}

        # Email extraction patterns
        self.email_patterns = [
            re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            re.compile(r'\bmailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b'),
        ]

        # Exclude patterns for unwanted emails
        self.exclude_patterns = [
            re.compile(r'@(example|test|sample|demo)\.com', re.IGNORECASE),
            re.compile(r'(noreply|no-reply|donotreply)', re.IGNORECASE),
            re.compile(r'@(10minutemail|tempmail|guerrillamail)', re.IGNORECASE),
        ]

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_session()

    async def start_session(self):
        """Initialize aiohttp session"""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=10,
            ttl_dns_cache=300,
            use_dns_cache=True
        )

        timeout = aiohttp.ClientTimeout(
            total=30,
            connect=10,
            sock_read=20
        )

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )

    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()

    def _get_user_agent(self) -> str:
        """Get a random user agent"""
        try:
            return self.user_agent_generator.random
        except Exception:
            return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

    async def _enforce_rate_limit(self, domain: str):
        """Enforce rate limiting per domain"""
        current_time = time.time()

        if domain in self.last_request_time:
            time_since_last = current_time - self.last_request_time[domain]
            min_delay = 1.0 / self.rate_config.requests_per_second

            if time_since_last < min_delay:
                delay = min_delay - time_since_last
                # Add random jitter to avoid thundering herd
                delay += random.uniform(0, 0.5)
                await asyncio.sleep(delay)

        self.last_request_time[domain] = time.time()

    def _check_robots_permission(self, url: str, user_agent: str) -> bool:
        """Check if robots.txt allows fetching this URL"""
        if not self.respect_robots or not self.robot_checker:
            return True

        return self.robot_checker.can_fetch(url, user_agent)

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL for rate limiting"""
        try:
            extracted = tldextract.extract(url)
            return f"{extracted.domain}.{extracted.suffix}"
        except Exception:
            return urlparse(url).netloc

    async def scrape_url(self, url: str, max_retries: int = 3) -> ScrapingResult:
        """Scrape a single URL with error handling and retries"""
        start_time = time.time()
        domain = self._extract_domain(url)
        user_agent = self._get_user_agent()

        # Check robots.txt permission
        if not self._check_robots_permission(url, user_agent):
            return ScrapingResult(
                url=url,
                success=False,
                error="Blocked by robots.txt"
            )

        # Enforce rate limiting
        await self._enforce_rate_limit(domain)

        for attempt in range(max_retries + 1):
            try:
                headers = {'User-Agent': user_agent}

                async with self.session.get(url, headers=headers) as response:
                    response_time = time.time() - start_time

                    if response.status == 200:
                        content = await response.text()

                        # Extract emails and links
                        emails = self._extract_emails(content)
                        links = self._extract_links(content, url)

                        return ScrapingResult(
                            url=url,
                            success=True,
                            status_code=response.status,
                            content=content,
                            emails=emails,
                            links=links,
                            response_time=response_time
                        )
                    else:
                        return ScrapingResult(
                            url=url,
                            success=False,
                            status_code=response.status,
                            error=f"HTTP {response.status}",
                            response_time=response_time
                        )

            except asyncio.TimeoutError:
                error_msg = "Request timeout"
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
            except aiohttp.ClientError as e:
                error_msg = f"Client error: {str(e)}"
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue

        return ScrapingResult(
            url=url,
            success=False,
            error=error_msg,
            response_time=time.time() - start_time
        )

    def _extract_emails(self, content: str) -> List[str]:
        """Extract email addresses from HTML content"""
        emails = set()

        for pattern in self.email_patterns:
            matches = pattern.findall(content)
            for match in matches:
                # Handle mailto: pattern that returns tuple
                email = match if isinstance(match, str) else match[0] if match else None
                if email:
                    emails.add(email.lower())

        # Filter out unwanted emails
        filtered_emails = []
        for email in emails:
            if not any(pattern.search(email) for pattern in self.exclude_patterns):
                filtered_emails.append(email)

        return filtered_emails

    def _extract_links(self, content: str, base_url: str) -> List[str]:
        """Extract links from HTML content"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            links = set()

            # Extract href attributes
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(base_url, href)

                # Filter out unwanted links
                if self._is_valid_link(absolute_url):
                    links.add(absolute_url)

            return list(links)

        except Exception as e:
            logger.warning(f"Error extracting links from {base_url}: {e}")
            return []

    def _is_valid_link(self, url: str) -> bool:
        """Check if a link is valid for crawling"""
        try:
            parsed = urlparse(url)

            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False

            # Only HTTP/HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False

            # Skip common non-content files
            unwanted_extensions = {
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico',
                '.zip', '.rar', '.tar', '.gz', '.mp3', '.mp4', '.avi'
            }

            if any(url.lower().endswith(ext) for ext in unwanted_extensions):
                return False

            # Skip common unwanted paths
            unwanted_paths = [
                '/admin', '/wp-admin', '/wp-content', '/cgi-bin',
                '/search', '/login', '/register', '/account',
                '/cart', '/checkout', '/api/', '/ajax/'
            ]

            if any(unwanted in parsed.path.lower() for unwanted in unwanted_paths):
                return False

            return True

        except Exception:
            return False

    async def scrape_multiple_urls(self, urls: List[str], max_concurrent: int = 10) -> List[ScrapingResult]:
        """Scrape multiple URLs concurrently with semaphore control"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_with_semaphore(url):
            async with semaphore:
                return await self.scrape_url(url)

        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ScrapingResult(
                    url=urls[i],
                    success=False,
                    error=f"Exception: {str(result)}"
                ))
            else:
                processed_results.append(result)

        return processed_results


class CompanyWebsiteScraper:
    """Specialized scraper for company websites"""

    def __init__(self, web_scraper: WebScraper):
        self.web_scraper = web_scraper

        # Common company page patterns
        self.target_paths = [
            '/',
            '/about',
            '/about-us',
            '/contact',
            '/contact-us',
            '/team',
            '/leadership',
            '/management',
            '/staff',
            '/people',
            '/careers',
            '/jobs',
            '/press',
            '/news'
        ]

    async def scrape_company_domain(self, domain: str, max_pages: int = 10) -> Dict[str, Any]:
        """Scrape a company domain comprehensively"""
        if not domain.startswith(('http://', 'https://')):
            base_url = f"https://{domain}"
        else:
            base_url = domain

        # Generate URLs to scrape
        urls_to_scrape = []
        for path in self.target_paths[:max_pages]:
            url = urljoin(base_url, path)
            urls_to_scrape.append(url)

        # Scrape all URLs
        results = await self.web_scraper.scrape_multiple_urls(urls_to_scrape)

        # Aggregate results
        all_emails = set()
        all_links = set()
        successful_pages = 0
        total_pages = len(results)

        for result in results:
            if result.success:
                successful_pages += 1
                all_emails.update(result.emails)
                all_links.update(result.links)

        # Extract additional pages from discovered links
        if successful_pages > 0 and len(all_emails) < 5:  # If we need more emails
            additional_urls = []
            for link in list(all_links)[:5]:  # Limit additional discovery
                parsed_link = urlparse(link)
                parsed_base = urlparse(base_url)

                # Only follow same-domain links
                if parsed_link.netloc == parsed_base.netloc:
                    additional_urls.append(link)

            if additional_urls:
                additional_results = await self.web_scraper.scrape_multiple_urls(additional_urls[:3])
                for result in additional_results:
                    if result.success:
                        all_emails.update(result.emails)
                        successful_pages += 1
                        total_pages += 1

        return {
            'domain': domain,
            'base_url': base_url,
            'emails_found': list(all_emails),
            'total_emails': len(all_emails),
            'pages_scraped': total_pages,
            'successful_pages': successful_pages,
            'success_rate': successful_pages / total_pages if total_pages > 0 else 0,
            'scraping_results': results
        }


# Utility functions for integration
async def scrape_company_list(domains: List[str], max_concurrent: int = 5) -> List[Dict[str, Any]]:
    """Scrape a list of company domains"""
    rate_config = RateLimitConfig(requests_per_second=2.0, delay_between_requests=0.5)

    async with WebScraper(rate_config=rate_config, respect_robots=True) as scraper:
        company_scraper = CompanyWebsiteScraper(scraper)

        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_company_with_semaphore(domain):
            async with semaphore:
                return await company_scraper.scrape_company_domain(domain)

        tasks = [scrape_company_with_semaphore(domain) for domain in domains]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'domain': domains[i],
                    'error': str(result),
                    'emails_found': [],
                    'total_emails': 0,
                    'success_rate': 0
                })
            else:
                processed_results.append(result)

        return processed_results


def extract_emails_from_search_results(search_html: str, max_emails: int = 50) -> List[str]:
    """Extract emails from search engine results pages"""
    scraper = WebScraper()
    emails = scraper._extract_emails(search_html)
    return emails[:max_emails]


# Example usage
if __name__ == "__main__":
    async def main():
        domains = ['example.com', 'test-company.com']
        results = await scrape_company_list(domains)

        for result in results:
            print(f"Domain: {result['domain']}")
            print(f"Emails found: {result['total_emails']}")
            print(f"Success rate: {result['success_rate']:.2%}")
            print(f"Emails: {result['emails_found']}")
            print("-" * 50)

    asyncio.run(main())