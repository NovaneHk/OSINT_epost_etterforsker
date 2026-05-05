"""
Enhanced theHarvester Connector for Phase 2
Advanced integration with theHarvester for comprehensive OSINT gathering
"""

import asyncio
import logging
import subprocess
import json
import tempfile
import os
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from .base_connector import BaseConnector
from integrations.connector_manager import OSINTResult
from core.error_handling import OSINTError, handle_errors

logger = logging.getLogger(__name__)

class TheHarvesterEnhanced(BaseConnector):
    """Enhanced theHarvester integration for comprehensive OSINT gathering"""

    # Available data sources in theHarvester
    AVAILABLE_SOURCES = [
        'baidu', 'bing', 'bingapi', 'bufferoverun', 'censys',
        'certspotter', 'crtsh', 'dnsdumpster', 'duckduckgo', 'fullhunt',
        'github-code', 'google', 'hackertarget', 'hunter', 'intelx',
        'linkedin', 'n45ht', 'omnisint', 'otx', 'pentesttools',
        'projectdiscovery', 'qwant', 'rapiddns', 'rocketreach',
        'securityTrails', 'shodan', 'spyse', 'sublist3r', 'threatcrowd',
        'trello', 'twitter', 'urlscan', 'virustotal', 'yahoo', 'zoomeye'
    ]

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.timeout = config.get('timeout', 60)
        self.max_retries = config.get('max_retries', 3)
        self.sources = config.get('sources', ['google', 'bing', 'linkedin'])
        self.limit = config.get('limit', 500)
        self.delay = config.get('delay', 1)
        self.use_shodan = config.get('use_shodan', False)
        self.shodan_key = config.get('shodan_api_key')
        self.tool_path = config.get('tool_path', 'theHarvester')

    def validate_config(self) -> bool:
        """Validate theHarvester configuration"""
        if not self._is_binary_available():
            logger.warning("theHarvester binary not found at path '%s'. Will use built-in scraper fallback.", self.tool_path)
            return False
        try:
            # Check if theHarvester is installed and accessible
            result = subprocess.run(
                [self.tool_path, '--help'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and 'theHarvester' in result.stdout:
                logger.info("theHarvester is available and accessible")
                return True
            else:
                logger.error("theHarvester not found or not working properly")
                return False

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.error(f"theHarvester validation failed: {e}")
            return False

    def _is_binary_available(self) -> bool:
        """Return True if the theHarvester binary can be found in PATH."""
        import shutil
        return shutil.which(self.tool_path) is not None

    def get_capabilities(self) -> List[str]:
        """Return list of supported capabilities"""
        return [
            'email_harvesting',
            'domain_reconnaissance',
            'subdomain_enumeration',
            'social_media_profiles',
            'linkedin_profiles',
            'twitter_profiles',
            'host_discovery',
            'certificate_transparency'
        ]

    @handle_errors
    async def search(self, query: str, **kwargs) -> List[OSINTResult]:
        """Execute theHarvester search with enhanced capabilities"""
        # Clean and validate the domain
        domain = self._clean_domain(query)
        if not self._validate_domain(domain):
            raise OSINTError(f"Invalid domain format: {domain}")

        # Get sources to use
        sources = kwargs.get('sources', self.sources)
        limit = kwargs.get('limit', self.limit)

        # Validate sources
        valid_sources = [s for s in sources if s in self.AVAILABLE_SOURCES]
        if not valid_sources:
            valid_sources = ['google', 'bing']  # Fallback to basic sources

        logger.info(f"Starting theHarvester search for {domain} using sources: {valid_sources}")

        all_results = []

        # Process each source individually for better error handling
        for source in valid_sources:
            try:
                source_results = await self._harvest_from_source(domain, source, limit, **kwargs)
                all_results.extend(source_results)

                # Add delay between sources to avoid rate limiting
                if self.delay > 0:
                    await asyncio.sleep(self.delay)

            except Exception as e:
                logger.error(f"Error harvesting from {source}: {e}")
                # Continue with other sources even if one fails

        # Deduplicate results
        deduplicated_results = self._deduplicate_results(all_results)

        logger.info(f"theHarvester completed: {len(deduplicated_results)} unique results from {len(valid_sources)} sources")

        return deduplicated_results

    async def _harvest_from_source(self, domain: str, source: str, limit: int, **kwargs) -> List[OSINTResult]:
        """Harvest data from a specific source"""
        # Create temporary file for output
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Build theHarvester command
            cmd = self._build_command(domain, source, limit, temp_path, **kwargs)

            logger.debug(f"Executing: {' '.join(cmd)}")

            # Execute theHarvester with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise OSINTError(f"theHarvester timeout for source {source}")

            # Check if process completed successfully
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.warning(f"theHarvester returned non-zero exit code for {source}: {error_msg}")
                # Don't raise error, just return empty results for this source
                return []

            # Parse results from output files and stdout
            results = await self._parse_results(temp_path, source, domain, stdout.decode())

            return results

        except Exception as e:
            logger.error(f"Error executing theHarvester for source {source}: {e}")
            return []

        finally:
            # Cleanup temporary files
            await self._cleanup_temp_files(temp_path)

    def _build_command(self, domain: str, source: str, limit: int, output_path: str, **kwargs) -> List[str]:
        """Build theHarvester command with all options"""
        cmd = [self.tool_path]

        # Basic parameters
        cmd.extend(['-d', domain])
        cmd.extend(['-b', source])
        cmd.extend(['-l', str(limit)])

        # Output format and file
        base_path = output_path.replace('.json', '')
        cmd.extend(['-f', base_path])

        # Additional options
        if self.delay > 0:
            cmd.extend(['--delay', str(self.delay)])

        if self.use_shodan and self.shodan_key:
            cmd.extend(['--shodan-key', self.shodan_key])

        # Optional parameters from kwargs
        if kwargs.get('dns_lookup', False):
            cmd.append('-n')

        if kwargs.get('dns_brute', False):
            cmd.append('-c')

        if kwargs.get('take_over', False):
            cmd.append('-t')

        if kwargs.get('port_scan', False):
            cmd.append('-p')

        return cmd

    async def _parse_results(self, base_path: str, source: str, domain: str, stdout: str) -> List[OSINTResult]:
        """Parse theHarvester results from multiple output formats"""
        results = []

        # Try to parse JSON output first (newer versions)
        json_results = await self._parse_json_output(base_path, source, domain)
        if json_results:
            results.extend(json_results)
        else:
            # Fallback to parsing stdout
            stdout_results = await self._parse_stdout_output(stdout, source, domain)
            results.extend(stdout_results)

        return results

    async def _parse_json_output(self, base_path: str, source: str, domain: str) -> List[OSINTResult]:
        """Parse JSON output from theHarvester"""
        json_path = f"{base_path}.json"

        if not os.path.exists(json_path):
            return []

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            results = []

            # Extract emails
            emails = data.get('emails', [])
            for email in emails:
                if self._validate_email(email):
                    result = OSINTResult(
                        source=f'theharvester_{source}',
                        data_type='email',
                        content={
                            'email': email,
                            'domain': domain,
                            'source': source,
                            'verified': False
                        },
                        confidence=0.8,
                        timestamp=datetime.now(),
                        metadata={
                            'harvester_source': source,
                            'target_domain': domain,
                            'extraction_method': 'json'
                        }
                    )
                    results.append(result)

            # Extract hosts/subdomains
            hosts = data.get('hosts', [])
            for host in hosts:
                if self._validate_domain(host):
                    result = OSINTResult(
                        source=f'theharvester_{source}',
                        data_type='subdomain',
                        content={
                            'subdomain': host,
                            'domain': domain,
                            'source': source,
                            'ip_address': None
                        },
                        confidence=0.7,
                        timestamp=datetime.now(),
                        metadata={
                            'harvester_source': source,
                            'target_domain': domain,
                            'extraction_method': 'json'
                        }
                    )
                    results.append(result)

            # Extract LinkedIn profiles
            linkedin_profiles = data.get('linkedin_people', [])
            for profile in linkedin_profiles:
                result = OSINTResult(
                    source=f'theharvester_{source}',
                    data_type='linkedin_profile',
                    content={
                        'profile_url': profile,
                        'domain': domain,
                        'source': source,
                        'platform': 'linkedin'
                    },
                    confidence=0.6,
                    timestamp=datetime.now(),
                    metadata={
                        'harvester_source': source,
                        'target_domain': domain,
                        'extraction_method': 'json'
                    }
                )
                results.append(result)

            # Extract Twitter profiles
            twitter_profiles = data.get('twitter_people', [])
            for profile in twitter_profiles:
                result = OSINTResult(
                    source=f'theharvester_{source}',
                    data_type='twitter_profile',
                    content={
                        'profile_url': profile,
                        'domain': domain,
                        'source': source,
                        'platform': 'twitter'
                    },
                    confidence=0.6,
                    timestamp=datetime.now(),
                    metadata={
                        'harvester_source': source,
                        'target_domain': domain,
                        'extraction_method': 'json'
                    }
                )
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error parsing JSON output: {e}")
            return []

    async def _parse_stdout_output(self, stdout: str, source: str, domain: str) -> List[OSINTResult]:
        """Parse stdout output when JSON is not available"""
        results = []

        # Extract emails using regex
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, stdout)

        for email in set(emails):  # Remove duplicates
            if self._validate_email(email):
                result = OSINTResult(
                    source=f'theharvester_{source}',
                    data_type='email',
                    content={
                        'email': email,
                        'domain': domain,
                        'source': source,
                        'verified': False
                    },
                    confidence=0.7,  # Lower confidence for regex extraction
                    timestamp=datetime.now(),
                    metadata={
                        'harvester_source': source,
                        'target_domain': domain,
                        'extraction_method': 'regex'
                    }
                )
                results.append(result)

        # Extract subdomains
        subdomain_pattern = rf'\b[\w.-]*\.{re.escape(domain)}\b'
        subdomains = re.findall(subdomain_pattern, stdout, re.IGNORECASE)

        for subdomain in set(subdomains):
            if self._validate_domain(subdomain) and subdomain != domain:
                result = OSINTResult(
                    source=f'theharvester_{source}',
                    data_type='subdomain',
                    content={
                        'subdomain': subdomain,
                        'domain': domain,
                        'source': source,
                        'ip_address': None
                    },
                    confidence=0.6,
                    timestamp=datetime.now(),
                    metadata={
                        'harvester_source': source,
                        'target_domain': domain,
                        'extraction_method': 'regex'
                    }
                )
                results.append(result)

        return results

    def _clean_domain(self, domain: str) -> str:
        """Clean and normalize domain"""
        domain = domain.strip().lower()

        # Remove protocol
        if domain.startswith(('http://', 'https://')):
            domain = domain.split('://', 1)[1]

        # Remove path
        if '/' in domain:
            domain = domain.split('/')[0]

        # Remove port
        if ':' in domain:
            domain = domain.split(':')[0]

        return domain

    def _validate_domain(self, domain: str) -> bool:
        """Validate domain format"""
        if not domain:
            return False

        # Basic domain validation
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(domain_pattern, domain)) and '.' in domain

    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        if not email:
            return False

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))

    def _deduplicate_results(self, results: List[OSINTResult]) -> List[OSINTResult]:
        """Remove duplicate results based on content"""
        seen = set()
        deduplicated = []

        for result in results:
            # Create a unique key based on data type and main content
            if result.data_type == 'email':
                key = f"email:{result.content.get('email', '')}"
            elif result.data_type == 'subdomain':
                key = f"subdomain:{result.content.get('subdomain', '')}"
            elif result.data_type in ['linkedin_profile', 'twitter_profile']:
                key = f"{result.data_type}:{result.content.get('profile_url', '')}"
            else:
                key = f"{result.data_type}:{json.dumps(result.content, sort_keys=True)}"

            if key not in seen:
                seen.add(key)
                deduplicated.append(result)

        return deduplicated

    async def _cleanup_temp_files(self, base_path: str):
        """Clean up temporary files created by theHarvester"""
        try:
            # theHarvester creates multiple output files
            extensions = ['.json', '.xml', '.html', '.txt']
            base = base_path.replace('.json', '')

            for ext in extensions:
                file_path = base + ext
                if os.path.exists(file_path):
                    os.unlink(file_path)

        except Exception as e:
            logger.warning(f"Error cleaning up temp files: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on theHarvester"""
        try:
            # Test basic functionality
            result = subprocess.run(
                [self.tool_path, '--help'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return {
                    'status': 'healthy',
                    'tool_available': True,
                    'version_info': 'theHarvester available',
                    'supported_sources': len(self.AVAILABLE_SOURCES)
                }
            else:
                return {
                    'status': 'unhealthy',
                    'tool_available': False,
                    'error': 'theHarvester not responding properly'
                }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'tool_available': False,
                'error': str(e)
            }

    def get_recommended_sources(self, target_type: str = 'general') -> List[str]:
        """Get recommended sources based on target type"""
        recommendations = {
            'general': ['google', 'bing', 'duckduckgo', 'yahoo'],
            'social': ['linkedin', 'twitter'],
            'technical': ['certspotter', 'crtsh', 'dnsdumpster', 'virustotal'],
            'comprehensive': ['google', 'bing', 'linkedin', 'certspotter', 'dnsdumpster', 'virustotal'],
            'fast': ['google', 'bing'],
            'deep': ['google', 'bing', 'linkedin', 'twitter', 'certspotter', 'crtsh', 'dnsdumpster']
        }

        return recommendations.get(target_type, recommendations['general'])
