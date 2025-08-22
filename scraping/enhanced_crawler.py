"""
Enhanced OSINT Crawler System
Real web scraping implementation with advanced email extraction
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import re
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from core.config import ConfigManager
from core.database import DatabaseManager, Contact, ContactStatus
from scraping.web_scraper import WebScraper, CompanyWebsiteScraper, RateLimitConfig, scrape_company_list
from extract.email_extractor import EmailExtractor

logger = logging.getLogger(__name__)


class EnhancedOSINTCrawler:
    """Enhanced crawler with real web scraping capabilities."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.db_manager = DatabaseManager()
        self.email_extractor = EmailExtractor(config_manager)
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

        # Add enhanced generic queries
        generic_queries = [
            f'"{persona}" AND "{sector}" AND "{geography}" contact email',
            f'site:linkedin.com/company {sector} {geography} contact',
            f'intitle:"{sector} directory" {geography} email',
            f'"{persona}" email {sector} {geography} -noreply',
            f'filetype:pdf "{sector} companies" {geography} contact',
            f'"{sector}" AND "{geography}" AND "contact us" email',
            f'site:crunchbase.com {sector} {geography}',
            f'"procurement" OR "purchasing" AND "{sector}" {geography} email'
        ]

        queries.extend(generic_queries)

        logger.info(f"Generated {len(queries)} search queries for {persona}/{sector}/{geography}")
        return queries

    def dry_run_crawl(self, source_types: List[str], limit: int) -> Dict[str, Any]:
        """Perform a dry run to estimate crawling scope."""

        sources_config = self.config_manager.load_sources()
        source_categories = sources_config.get('source_categories', {})

        estimated_pages = 0
        estimated_emails = 0
        source_breakdown = {}

        for source_type in source_types:
            if source_type in source_categories:
                category = source_categories[source_type]
                sources = category.get('sources', [])
                enabled_sources = [s for s in sources if s.get('enabled', True)]

                # Estimate pages per source based on source type
                if source_type == 'directories':
                    pages_per_source = min(limit // len(enabled_sources) if enabled_sources else 0, 20)
                    emails_per_page = 5
                elif source_type == 'events':
                    pages_per_source = min(limit // len(enabled_sources) if enabled_sources else 0, 10)
                    emails_per_page = 8
                elif source_type == 'sites':
                    pages_per_source = 5  # Multiple pages per company site
                    emails_per_page = 3
                else:
                    pages_per_source = 10
                    emails_per_page = 4

                total_pages = pages_per_source * len(enabled_sources)
                total_emails = total_pages * emails_per_page

                estimated_pages += total_pages
                estimated_emails += total_emails
                source_breakdown[source_type] = {
                    'sources_count': len(enabled_sources),
                    'estimated_pages': total_pages,
                    'estimated_emails': total_emails
                }

        return {
            'estimated_pages': estimated_pages,
            'estimated_emails': estimated_emails,
            'source_breakdown': source_breakdown,
            'estimated_duration_minutes': estimated_pages * 3  # 3 seconds per page average with rate limiting
        }

    async def crawl_sources(self, source_types: List[str], concurrent_workers: int,
                           rate_limit: float, limit: int, respect_robots: bool) -> Dict[str, Any]:
        """Execute real crawling across multiple source types."""

        logger.info(f"Starting enhanced crawl with {concurrent_workers} workers, rate limit: {rate_limit}/s")

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
                    result = await self._crawl_directories_enhanced(
                        source_categories[source_type],
                        concurrent_workers,
                        rate_limit,
                        limit,
                        respect_robots
                    )
                elif source_type == 'events':
                    result = await self._crawl_events_enhanced(
                        source_categories[source_type],
                        concurrent_workers,
                        rate_limit,
                        limit,
                        respect_robots
                    )
                elif source_type == 'sites':
                    result = await self._crawl_company_sites_enhanced(
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
                    'emails_extracted': 0,
                    'success_rate': 0.0
                }

        return results

    async def _crawl_directories_enhanced(self, category_config: Dict[str, Any],
                                        concurrent_workers: int, rate_limit: float,
                                        limit: int, respect_robots: bool) -> Dict[str, Any]:
        """Crawl business directory sources using real web scraping."""

        sources = category_config.get('sources', [])
        enabled_sources = [s for s in sources if s.get('enabled', True)]

        total_pages = 0
        total_companies = 0
        total_emails = 0
        successful_requests = 0
        total_requests = 0

        # Configure rate limiting
        rate_config = RateLimitConfig(
            requests_per_second=rate_limit,
            delay_between_requests=1.0 / rate_limit
        )

        async with WebScraper(rate_config=rate_config, respect_robots=respect_robots) as scraper:
            for source in enabled_sources[:limit]:
                try:
                    logger.info(f"Crawling directory: {source['name']}")
                    source_url = source['url']

                    # Scrape the directory page
                    result = await scraper.scrape_url(source_url)
                    total_requests += 1

                    if result.success:
                        successful_requests += 1
                        total_pages += 1

                        # Extract company information from the scraped content
                        companies_data = await self._extract_companies_from_directory(
                            result.content, source_url, source
                        )

                        # Store companies and extract emails
                        for company_data in companies_data:
                            self.db_manager.store_company(company_data)
                            total_companies += 1

                            # Extract emails from scraped content
                            emails_found = result.emails
                            for email in emails_found:
                                await self._store_extracted_email(
                                    email, company_data, source_url, 'directory'
                                )
                                total_emails += 1

                        # Process additional directory pages if available
                        additional_urls = [link for link in result.links
                                         if self._is_directory_related_link(link, source_url)][:3]

                        for additional_url in additional_urls:
                            if total_pages >= limit:
                                break

                            additional_result = await scraper.scrape_url(additional_url)
                            total_requests += 1

                            if additional_result.success:
                                successful_requests += 1
                                total_pages += 1

                                additional_companies = await self._extract_companies_from_directory(
                                    additional_result.content, additional_url, source
                                )

                                for company_data in additional_companies:
                                    self.db_manager.store_company(company_data)
                                    total_companies += 1

                                    # Extract emails from additional pages
                                    for email in additional_result.emails:
                                        await self._store_extracted_email(
                                            email, company_data, additional_url, 'directory'
                                        )
                                        total_emails += 1

                except Exception as e:
                    logger.error(f"Error crawling {source['name']}: {e}")
                    total_requests += 1

        success_rate = successful_requests / total_requests if total_requests > 0 else 0

        return {
            'pages_crawled': total_pages,
            'companies_found': total_companies,
            'emails_extracted': total_emails,
            'success_rate': success_rate,
            'sources_processed': len(enabled_sources)
        }

    async def _crawl_events_enhanced(self, category_config: Dict[str, Any],
                                   concurrent_workers: int, rate_limit: float,
                                   limit: int, respect_robots: bool) -> Dict[str, Any]:
        """Crawl event and conference sources using real web scraping."""

        sources = category_config.get('sources', [])
        enabled_sources = [s for s in sources if s.get('enabled', True)]

        total_pages = 0
        total_companies = 0
        total_emails = 0
        successful_requests = 0
        total_requests = 0

        rate_config = RateLimitConfig(
            requests_per_second=rate_limit,
            delay_between_requests=1.0 / rate_limit
        )

        async with WebScraper(rate_config=rate_config, respect_robots=respect_robots) as scraper:
            for source in enabled_sources[:limit]:
                try:
                    logger.info(f"Crawling event: {source['name']}")
                    source_url = source['url']

                    # Scrape the event page
                    result = await scraper.scrape_url(source_url)
                    total_requests += 1

                    if result.success:
                        successful_requests += 1
                        total_pages += 1

                        # Extract company/attendee information from events
                        companies_data = await self._extract_companies_from_event(
                            result.content, source_url, source
                        )

                        # Store companies and emails
                        for company_data in companies_data:
                            self.db_manager.store_company(company_data)
                            total_companies += 1

                            # Extract emails from event content
                            for email in result.emails:
                                await self._store_extracted_email(
                                    email, company_data, source_url, 'event'
                                )
                                total_emails += 1

                        # Look for speaker/attendee pages
                        event_related_links = [link for link in result.links
                                             if self._is_event_related_link(link, source_url)][:5]

                        for event_link in event_related_links:
                            if total_pages >= limit:
                                break

                            event_result = await scraper.scrape_url(event_link)
                            total_requests += 1

                            if event_result.success:
                                successful_requests += 1
                                total_pages += 1

                                for email in event_result.emails:
                                    await self._store_extracted_email(
                                        email, {'name': 'Event Participant', 'domain': 'unknown'},
                                        event_link, 'event'
                                    )
                                    total_emails += 1

                except Exception as e:
                    logger.error(f"Error crawling event {source['name']}: {e}")
                    total_requests += 1

        success_rate = successful_requests / total_requests if total_requests > 0 else 0

        return {
            'pages_crawled': total_pages,
            'companies_found': total_companies,
            'emails_extracted': total_emails,
            'success_rate': success_rate,
            'sources_processed': len(enabled_sources)
        }

    async def _crawl_company_sites_enhanced(self, category_config: Dict[str, Any],
                                          concurrent_workers: int, rate_limit: float,
                                          limit: int, respect_robots: bool) -> Dict[str, Any]:
        """Crawl individual company websites using enhanced scraping."""

        # Get companies from database to crawl their sites
        companies = self.db_manager.get_companies(limit=limit)

        total_pages = 0
        total_companies = 0
        total_emails = 0
        successful_requests = 0
        total_requests = 0

        rate_config = RateLimitConfig(
            requests_per_second=rate_limit,
            delay_between_requests=1.0 / rate_limit
        )

        async with WebScraper(rate_config=rate_config, respect_robots=respect_robots) as scraper:
            company_scraper = CompanyWebsiteScraper(scraper)

            for company in companies:
                try:
                    domain = company.get('domain', '')
                    if not domain:
                        continue

                    logger.info(f"Crawling company site: {domain}")

                    # Use specialized company scraper
                    scraping_result = await company_scraper.scrape_company_domain(domain, max_pages=5)
                    
                    total_requests += scraping_result['pages_scraped']
                    successful_requests += scraping_result['successful_pages']
                    total_pages += scraping_result['pages_scraped']
                    total_companies += 1

                    # Store extracted emails
                    for email in scraping_result['emails_found']:
                        await self._store_extracted_email(
                            email, company, domain, 'company_site'
                        )
                        total_emails += 1

                    # Update company with additional scraped info
                    updated_data = {
                        'name': company.get('name', 'Unknown'),
                        'domain': domain,
                        'url': scraping_result['base_url'],
                        'industry': company.get('industry', 'Unknown'),
                        'source_url': scraping_result['base_url'],
                        'source_type': 'company_site',
                        'credibility_score': 80,  # Company sites have high credibility
                        'retrieved_at': datetime.now().isoformat(),
                        'emails_found': len(scraping_result['emails_found']),
                        'scraping_success_rate': scraping_result['success_rate']
                    }
                    self.db_manager.store_company(updated_data)

                except Exception as e:
                    logger.error(f"Error crawling company {company.get('name', '')}: {e}")
                    total_requests += 1

        success_rate = successful_requests / total_requests if total_requests > 0 else 0

        return {
            'pages_crawled': total_pages,
            'companies_found': total_companies,
            'emails_extracted': total_emails,
            'success_rate': success_rate,
            'sources_processed': len(companies)
        }

    async def _extract_companies_from_directory(self, html_content: str, source_url: str,
                                              source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract company information from business directory pages."""
        companies = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Common patterns for business listings
            listing_selectors = [
                '.listing', '.business-listing', '.company-listing',
                '.directory-item', '.business-item', '.company-item',
                '.entry', '.business-entry', '.company-entry'
            ]
            
            listings = []
            for selector in listing_selectors:
                found_listings = soup.select(selector)
                if found_listings:
                    listings.extend(found_listings)
                    break
            
            # If no specific listings found, look for structured data
            if not listings:
                # Look for repeated patterns that might be company listings
                potential_listings = soup.find_all(['div', 'li', 'article'],
                                                 class_=re.compile(r'(company|business|listing|entry)'))
                listings = potential_listings[:20]  # Limit to avoid noise
            
            for listing in listings:
                try:
                    company_data = self._extract_company_from_listing(listing, source_url, source)
                    if company_data:
                        companies.append(company_data)
                except Exception as e:
                    logger.debug(f"Error extracting company from listing: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing directory content from {source_url}: {e}")
        
        return companies

    def _extract_company_from_listing(self, listing_element, source_url: str,
                                    source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract company data from a single listing element."""
        try:
            # Look for company name
            name_selectors = ['h1', 'h2', 'h3', '.name', '.company-name', '.business-name', 'a']
            name = None
            
            for selector in name_selectors:
                name_element = listing_element.select_one(selector)
                if name_element:
                    name = name_element.get_text(strip=True)
                    if name and len(name) > 2:
                        break
            
            if not name:
                return None
            
            # Look for website/domain
            domain = None
            website_link = listing_element.find('a', href=re.compile(r'https?://'))
            if website_link:
                href = website_link.get('href', '')
                if href.startswith('http'):
                    parsed = urlparse(href)
                    domain = parsed.netloc
            
            # Generate domain if not found
            if not domain:
                # Try to generate domain from company name
                clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name.lower())
                domain_name = clean_name.replace(' ', '')[:20]
                domain = f"{domain_name}.com"  # This is speculative
            
            return {
                'name': name,
                'domain': domain,
                'url': f"https://{domain}" if domain else None,
                'industry': self._guess_industry_from_content(listing_element.get_text()),
                'source_url': source_url,
                'source_type': 'directory',
                'credibility_score': source.get('credibility_score', 60),
                'retrieved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.debug(f"Error extracting company from listing: {e}")
            return None

    async def _extract_companies_from_event(self, html_content: str, source_url: str,
                                          source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract company information from event pages."""
        companies = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for sponsor sections, exhibitor lists, speaker companies
            company_sections = soup.find_all(['div', 'section'],
                                           class_=re.compile(r'(sponsor|exhibitor|speaker|company|partner)'))
            
            for section in company_sections:
                # Extract company names and try to find associated links
                company_links = section.find_all('a', href=True)
                for link in company_links:
                    company_name = link.get_text(strip=True)
                    if len(company_name) > 2:
                        href = link.get('href', '')
                        domain = None
                        
                        if href.startswith('http'):
                            parsed = urlparse(href)
                            domain = parsed.netloc
                        
                        if not domain:
                            # Generate speculative domain
                            clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', company_name.lower())
                            domain_name = clean_name.replace(' ', '')[:15]
                            domain = f"{domain_name}.com"
                        
                        companies.append({
                            'name': company_name,
                            'domain': domain,
                            'url': href if href.startswith('http') else f"https://{domain}",
                            'industry': 'Event Participant',
                            'source_url': source_url,
                            'source_type': 'event',
                            'credibility_score': source.get('credibility_score', 55),
                            'retrieved_at': datetime.now().isoformat()
                        })
                        
        except Exception as e:
            logger.error(f"Error parsing event content from {source_url}: {e}")
        
        return companies[:50]  # Limit to avoid too much noise

    async def _store_extracted_email(self, email: str, company_data: Dict[str, Any],
                                   source_url: str, source_type: str):
        """Store an extracted email in the database."""
        try:
            # Create contact record
            contact = Contact(
                email=email,
                domain=email.split('@')[1] if '@' in email else 'unknown',
                name=None,  # Will be enriched later
                role=self._guess_role_from_email(email),
                company=company_data.get('name', 'Unknown'),
                sector=company_data.get('industry', 'Unknown'),
                source=source_url,
                confidence_score=self._calculate_email_confidence(email, source_type),
                status=ContactStatus.UNVALIDATED
            )
            
            # Store in database
            self.db_manager.add_contact(contact)
            
        except Exception as e:
            logger.debug(f"Error storing email {email}: {e}")

    def _is_directory_related_link(self, link: str, base_url: str) -> bool:
        """Check if a link is related to directory listings."""
        directory_indicators = ['listing', 'directory', 'companies', 'businesses', 'page', 'category']
        link_lower = link.lower()
        return any(indicator in link_lower for indicator in directory_indicators)

    def _is_event_related_link(self, link: str, base_url: str) -> bool:
        """Check if a link is related to event content."""
        event_indicators = ['speaker', 'exhibitor', 'sponsor', 'attendee', 'participant', 'agenda']
        link_lower = link.lower()
        return any(indicator in link_lower for indicator in event_indicators)

    def _guess_industry_from_content(self, content: str) -> str:
        """Guess industry from text content."""
        content_lower = content.lower()
        
        industry_keywords = {
            'technology': ['software', 'tech', 'digital', 'ai', 'data', 'cloud', 'saas'],
            'finance': ['bank', 'financial', 'investment', 'insurance', 'fintech'],
            'healthcare': ['health', 'medical', 'pharma', 'hospital', 'clinical'],
            'manufacturing': ['manufacturing', 'industrial', 'factory', 'production'],
            'retail': ['retail', 'consumer', 'shopping', 'ecommerce', 'store'],
            'consulting': ['consulting', 'advisory', 'professional services']
        }
        
        for industry, keywords in industry_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return industry.title()
        
        return 'Other'

    def _guess_role_from_email(self, email: str) -> Optional[str]:
        """Guess role from email address."""
        local_part = email.split('@')[0].lower()
        
        role_patterns = {
            'CEO': ['ceo', 'chief.executive'],
            'CTO': ['cto', 'chief.technology'],
            'CFO': ['cfo', 'chief.financial'],
            'Sales': ['sales', 'business', 'commercial'],
            'Marketing': ['marketing', 'pr', 'communications'],
            'Support': ['support', 'help', 'service'],
            'HR': ['hr', 'human.resources', 'recruiting'],
            'Operations': ['ops', 'operations', 'admin'],
            'Procurement': ['procurement', 'purchasing', 'sourcing']
        }
        
        for role, patterns in role_patterns.items():
            if any(pattern in local_part for pattern in patterns):
                return role
        
        return None

    def _calculate_email_confidence(self, email: str, source_type: str) -> float:
        """Calculate confidence score for extracted email."""
        confidence = 0.5  # Base confidence
        
        # Source type bonus
        source_bonuses = {
            'company_site': 0.3,
            'directory': 0.2,
            'event': 0.15
        }
        confidence += source_bonuses.get(source_type, 0.1)
        
        # Email pattern bonus
        local_part = email.split('@')[0].lower()
        if any(term in local_part for term in ['info', 'contact', 'sales', 'support']):
            confidence += 0.1
        if any(term in local_part for term in ['ceo', 'cto', 'director', 'manager']):
            confidence += 0.15
        
        # Penalty for suspicious patterns
        if any(term in local_part for term in ['noreply', 'no-reply', 'test']):
            confidence -= 0.3
        
        return max(0.0, min(1.0, confidence))