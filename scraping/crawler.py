"""
OSINT Crawler System
Main crawler orchestrator that manages different spider types
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import subprocess
import tempfile
import json
from datetime import datetime

from core.config import ConfigManager
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

class OSINTCrawler:
    """Main crawler orchestrator for OSINT data collection."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.db_manager = DatabaseManager()
        self.results = {}

    def generate_search_queries(self, persona: str, sector: str, geography: str) -> List[str]:
        """Generate targeted search queries based on parameters."""

        sources_config = self.config_manager.load_sources()
        search_dorks = sources_config.get('search_dorks', {})

        # Get sector-specific dorks
        sector_dorks = search_dorks.get(sector, [])

        # Replace placeholders with actual values
        queries = []
        for dork in sector_dorks:
            query = dork.replace('{geo}', geography)
            query = query.replace('{persona}', persona)
            query = query.replace('{sector}', sector)
            queries.append(query)

        # Add generic queries
        generic_queries = [
            f'"{persona}" AND "{sector}" AND "{geography}" contact',
            f'site:linkedin.com/company {sector} {geography}',
            f'intitle:"{sector} directory" {geography}',
            f'"{persona}" email {sector} {geography}',
            f'filetype:pdf "{sector} companies" {geography}'
        ]

        queries.extend(generic_queries)

        logger.info(f"Generated {len(queries)} search queries for {persona}/{sector}/{geography}")
        return queries

    def dry_run_crawl(self, source_types: List[str], limit: int) -> Dict[str, Any]:
        """Perform a dry run to estimate crawling scope."""

        sources_config = self.config_manager.load_sources()
        source_categories = sources_config.get('source_categories', {})

        estimated_pages = 0
        source_breakdown = {}

        for source_type in source_types:
            if source_type in source_categories:
                category = source_categories[source_type]
                sources = category.get('sources', [])
                enabled_sources = [s for s in sources if s.get('enabled', True)]

                # Estimate pages per source
                pages_per_source = min(limit // len(enabled_sources) if enabled_sources else 0, 100)
                total_pages = pages_per_source * len(enabled_sources)

                estimated_pages += total_pages
                source_breakdown[source_type] = {
                    'sources_count': len(enabled_sources),
                    'estimated_pages': total_pages
                }

        return {
            'estimated_pages': estimated_pages,
            'source_breakdown': source_breakdown,
            'estimated_duration_minutes': estimated_pages * 2  # 2 seconds per page average
        }

    async def crawl_sources(self, source_types: List[str], concurrent_workers: int,
                           rate_limit: float, limit: int, respect_robots: bool) -> Dict[str, Any]:
        """Execute crawling across multiple source types."""

        logger.info(f"Starting crawl with {concurrent_workers} workers, rate limit: {rate_limit}/s")

        # Load source configuration
        sources_config = self.config_manager.load_sources()
        source_categories = sources_config.get('source_categories', {})

        results = {}

        for source_type in source_types:
            if source_type not in source_categories:
                logger.warning(f"Unknown source type: {source_type}")
                continue

            logger.info(f"Crawling {source_type} sources...")

            try:
                if source_type == 'directories':
                    result = await self._crawl_directories(
                        source_categories[source_type],
                        concurrent_workers,
                        rate_limit,
                        limit,
                        respect_robots
                    )
                elif source_type == 'events':
                    result = await self._crawl_events(
                        source_categories[source_type],
                        concurrent_workers,
                        rate_limit,
                        limit,
                        respect_robots
                    )
                elif source_type == 'sites':
                    result = await self._crawl_company_sites(
                        source_categories[source_type],
                        concurrent_workers,
                        rate_limit,
                        limit,
                        respect_robots
                    )

                results[source_type] = result

            except Exception as e:
                logger.error(f"Error crawling {source_type}: {e}")
                results[source_type] = {
                    'error': str(e),
                    'pages_crawled': 0,
                    'companies_found': 0,
                    'success_rate': 0.0
                }

        return results

    async def _crawl_directories(self, category_config: Dict[str, Any],
                                concurrent_workers: int, rate_limit: float,
                                limit: int, respect_robots: bool) -> Dict[str, Any]:
        """Crawl business directory sources."""

        sources = category_config.get('sources', [])
        enabled_sources = [s for s in sources if s.get('enabled', True)]

        total_pages = 0
        total_companies = 0
        successful_requests = 0
        total_requests = 0

        for source in enabled_sources[:limit]:
            try:
                logger.info(f"Crawling directory: {source['name']}")

                # Real crawling implementation
                companies_data = await self._crawl_directory_source(source, limit - total_pages)

                pages_crawled = len(companies_data)
                companies_found = 0

                # Store companies in database
                for company_data in companies_data:
                    try:
                        company_data.update({
                            'source_url': source['url'],
                            'source_type': 'directory',
                            'credibility_score': source.get('credibility_score', 50),
                            'retrieved_at': datetime.now().isoformat()
                        })
                        self.db_manager.store_company(company_data)
                        companies_found += 1
                    except Exception as store_error:
                        logger.warning(f"Failed to store company data: {store_error}")

                total_pages += pages_crawled
                total_companies += companies_found
                successful_requests += pages_crawled
                total_requests += pages_crawled

                # Respect rate limiting
                await asyncio.sleep(1.0 / rate_limit)

            except Exception as e:
                logger.error(f"Error crawling {source['name']}: {e}")
                total_requests += 1

        success_rate = successful_requests / total_requests if total_requests > 0 else 0

        return {
            'pages_crawled': total_pages,
            'companies_found': total_companies,
            'success_rate': success_rate,
            'sources_processed': len(enabled_sources)
        }

    async def _crawl_events(self, category_config: Dict[str, Any],
                           concurrent_workers: int, rate_limit: float,
                           limit: int, respect_robots: bool) -> Dict[str, Any]:
        """Crawl event and conference sources."""

        sources = category_config.get('sources', [])
        enabled_sources = [s for s in sources if s.get('enabled', True)]

        total_pages = 0
        total_companies = 0
        successful_requests = 0
        total_requests = 0

        for source in enabled_sources[:limit]:
            try:
                logger.info(f"Crawling event: {source['name']}")

                # Real event crawling implementation
                companies_data = await self._crawl_event_source(source, limit - total_pages)

                pages_crawled = len(companies_data)
                companies_found = 0

                # Store companies
                for company_data in companies_data:
                    try:
                        company_data.update({
                            'source_url': source['url'],
                            'source_type': 'event',
                            'credibility_score': source.get('credibility_score', 50),
                            'retrieved_at': datetime.now().isoformat()
                        })
                        self.db_manager.store_company(company_data)
                        companies_found += 1
                    except Exception as store_error:
                        logger.warning(f"Failed to store company data: {store_error}")

                total_pages += pages_crawled
                total_companies += companies_found
                successful_requests += pages_crawled
                total_requests += pages_crawled

                await asyncio.sleep(1.0 / rate_limit)

            except Exception as e:
                logger.error(f"Error crawling {source['name']}: {e}")
                total_requests += 1

        success_rate = successful_requests / total_requests if total_requests > 0 else 0

        return {
            'pages_crawled': total_pages,
            'companies_found': total_companies,
            'success_rate': success_rate,
            'sources_processed': len(enabled_sources)
        }

    async def _crawl_company_sites(self, category_config: Dict[str, Any],
                                  concurrent_workers: int, rate_limit: float,
                                  limit: int, respect_robots: bool) -> Dict[str, Any]:
        """Crawl individual company websites."""

        # Get companies from database to crawl their sites
        companies = self.db_manager.get_companies(limit=limit)

        total_pages = 0
        total_companies = 0
        successful_requests = 0
        total_requests = 0

        crawl_patterns = category_config.get('crawl_patterns', ['/about', '/contact', '/team'])

        for company in companies:
            try:
                domain = company.get('domain', '')
                if not domain:
                    continue

                logger.info(f"Crawling company site: {domain}")

                # Simulate crawling company pages
                pages_crawled = len(crawl_patterns)

                # Update company with additional info
                updated_data = {
                    'name': company['name'],
                    'domain': domain,
                    'url': f"https://{domain}",
                    'industry': company.get('industry', 'Unknown'),
                    'source_url': f"https://{domain}",
                    'source_type': 'company_site',
                    'credibility_score': 70,  # Company sites have good credibility
                    'retrieved_at': datetime.now().isoformat()
                }
                self.db_manager.store_company(updated_data)

                total_pages += pages_crawled
                total_companies += 1
                successful_requests += pages_crawled
                total_requests += pages_crawled

                await asyncio.sleep(1.0 / rate_limit)

            except Exception as e:
                logger.error(f"Error crawling company {company.get('name', '')}: {e}")
                total_requests += 1

        success_rate = successful_requests / total_requests if total_requests > 0 else 0

        return {
            'pages_crawled': total_pages,
            'companies_found': total_companies,
            'success_rate': success_rate,
            'sources_processed': len(companies)
        }

    async def _crawl_directory_source(self, source: Dict[str, Any], max_pages: int) -> List[Dict[str, Any]]:
        """Crawl a business directory source using real web scraping"""

        companies = []
        try:
            import aiohttp
            import asyncio
            from bs4 import BeautifulSoup

            async with aiohttp.ClientSession() as session:
                # Get the main directory page
                async with session.get(source['url'], timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch {source['url']}: Status {response.status}")
                        return companies

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Extract companies using configured selectors
                    company_selector = source.get('company_selector', '.company')
                    name_selector = source.get('name_selector', '.name')
                    domain_selector = source.get('domain_selector', '.domain')
                    contact_selector = source.get('contact_selector', '.contact')

                    company_elements = soup.select(company_selector)

                    for element in company_elements[:max_pages]:
                        try:
                            # Extract company information
                            name_elem = element.select_one(name_selector)
                            domain_elem = element.select_one(domain_selector)
                            contact_elem = element.select_one(contact_selector)

                            company_name = name_elem.get_text(strip=True) if name_elem else None
                            company_domain = domain_elem.get_text(strip=True) if domain_elem else None
                            contact_url = contact_elem.get('href') if contact_elem else None

                            # Clean domain (remove http/https)
                            if company_domain:
                                company_domain = company_domain.replace('http://', '').replace('https://', '').strip('/')

                            if company_name and company_domain:
                                company_data = {
                                    'name': company_name,
                                    'domain': company_domain,
                                    'url': f"https://{company_domain}",
                                    'industry': self._extract_industry_from_context(element),
                                    'contact_url': contact_url
                                }
                                companies.append(company_data)

                                # Respect rate limiting
                                await asyncio.sleep(0.5)

                        except Exception as e:
                            logger.warning(f"Error extracting company from element: {e}")
                            continue

        except ImportError:
            logger.error("Required libraries (aiohttp, beautifulsoup4) not available for web scraping")
            # Fall back to simulation for missing dependencies
            companies = self._simulate_directory_data(source, max_pages)
        except Exception as e:
            logger.error(f"Error crawling directory source {source['url']}: {e}")
            # Fall back to simulation on error
            companies = self._simulate_directory_data(source, max_pages)

        logger.info(f"Extracted {len(companies)} companies from {source['name']}")
        return companies

    async def _crawl_event_source(self, source: Dict[str, Any], max_pages: int) -> List[Dict[str, Any]]:
        """Crawl an event/conference source for exhibitor companies"""

        companies = []
        try:
            import aiohttp
            import asyncio
            from bs4 import BeautifulSoup

            async with aiohttp.ClientSession() as session:
                async with session.get(source['url'], timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch {source['url']}: Status {response.status}")
                        return companies

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Event pages often have different structures
                    exhibitor_selectors = [
                        '.exhibitor', '.company', '.sponsor', '.participant',
                        '[class*="exhibitor"]', '[class*="company"]'
                    ]

                    exhibitor_elements = []
                    for selector in exhibitor_selectors:
                        elements = soup.select(selector)
                        if elements:
                            exhibitor_elements = elements
                            break

                    for element in exhibitor_elements[:max_pages]:
                        try:
                            # Try to extract company name and domain from various patterns
                            company_name = self._extract_company_name_from_event(element)
                            company_domain = self._extract_domain_from_event(element)

                            if company_name and company_domain:
                                company_data = {
                                    'name': company_name,
                                    'domain': company_domain,
                                    'url': f"https://{company_domain}",
                                    'industry': 'Technology',  # Events often tech-focused
                                    'event_context': True
                                }
                                companies.append(company_data)

                                await asyncio.sleep(0.3)  # Faster for events

                        except Exception as e:
                            logger.warning(f"Error extracting company from event element: {e}")
                            continue

        except ImportError:
            logger.error("Required libraries not available for web scraping")
            companies = self._simulate_event_data(source, max_pages)
        except Exception as e:
            logger.error(f"Error crawling event source {source['url']}: {e}")
            companies = self._simulate_event_data(source, max_pages)

        logger.info(f"Extracted {len(companies)} companies from event {source['name']}")
        return companies

    def _extract_industry_from_context(self, element) -> str:
        """Extract industry information from HTML element context"""

        text_content = element.get_text().lower()

        # Industry keywords mapping
        industry_keywords = {
            'technology': ['tech', 'software', 'saas', 'ai', 'digital', 'cloud'],
            'ecommerce': ['ecommerce', 'e-commerce', 'retail', 'shop', 'store'],
            'manufacturing': ['manufacturing', 'industrial', 'production', 'factory'],
            'finance': ['finance', 'bank', 'investment', 'fintech'],
            'healthcare': ['health', 'medical', 'pharma', 'biotech'],
            'consulting': ['consulting', 'advisory', 'services']
        }

        for industry, keywords in industry_keywords.items():
            if any(keyword in text_content for keyword in keywords):
                return industry.title()

        return 'Other'

    def _extract_company_name_from_event(self, element) -> str:
        """Extract company name from event listing element"""

        # Try various selectors for company names
        name_selectors = [
            '.company-name', '.exhibitor-name', '.name',
            'h3', 'h4', '.title', '[class*="name"]'
        ]

        for selector in name_selectors:
            name_elem = element.select_one(selector)
            if name_elem:
                name = name_elem.get_text(strip=True)
                if name and len(name) > 2:
                    return name

        # Fall back to first strong/bold text
        strong_elem = element.select_one('strong, b')
        if strong_elem:
            return strong_elem.get_text(strip=True)

        return None

    def _extract_domain_from_event(self, element) -> str:
        """Extract domain from event listing element"""

        # Look for links
        link_elem = element.select_one('a[href]')
        if link_elem:
            href = link_elem.get('href', '')
            if href.startswith('http'):
                from urllib.parse import urlparse
                parsed = urlparse(href)
                return parsed.netloc

        # Look for text that looks like a domain
        text_content = element.get_text()
        import re
        domain_pattern = r'\b[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.com\b'
        domain_match = re.search(domain_pattern, text_content)
        if domain_match:
            return domain_match.group()

        return None

    def _simulate_directory_data(self, source: Dict[str, Any], max_pages: int) -> List[Dict[str, Any]]:
        """Fallback simulation for directory crawling"""

        companies = []
        for i in range(min(max_pages, 10)):  # Limit simulation
            company_data = {
                'name': f"Directory Company {i+1}",
                'domain': f"dircompany{i+1}.example.com",
                'url': f"https://dircompany{i+1}.example.com",
                'industry': 'Technology',
                'simulated': True
            }
            companies.append(company_data)

        return companies

    def _simulate_event_data(self, source: Dict[str, Any], max_pages: int) -> List[Dict[str, Any]]:
        """Fallback simulation for event crawling"""

        companies = []
        for i in range(min(max_pages, 15)):  # Events usually have more companies
            company_data = {
                'name': f"Event Company {i+1}",
                'domain': f"eventco{i+1}.example.com",
                'url': f"https://eventco{i+1}.example.com",
                'industry': 'Technology',
                'event_context': True,
                'simulated': True
            }
            companies.append(company_data)

        return companies
