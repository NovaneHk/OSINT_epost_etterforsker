"""
theHarvester Connector
Integration with theHarvester OSINT tool for email and subdomain gathering
"""

import asyncio
import json
import logging
import tempfile
from typing import Dict, List, Any, Optional
from pathlib import Path
import re

from .base_connector import CLIConnector, ConnectorResult
from core.error_handling import NetworkError, ValidationError

logger = logging.getLogger(__name__)


class TheHarvesterConnector(CLIConnector):
    """Connector for theHarvester tool integration"""

    # Available data sources in theHarvester
    AVAILABLE_SOURCES = [
        'all', 'baidu', 'bing', 'bingapi', 'bufferoverun', 'censys',
        'certspotter', 'crtsh', 'dnsdumpster', 'duckduckgo', 'fullhunt',
        'github-code', 'google', 'hackertarget', 'hunter', 'intelx',
        'linkedin', 'n45ht', 'omnisint', 'otx', 'pentesttools',
        'projectdiscovery', 'qwant', 'rapiddns', 'rocketreach',
        'securityTrails', 'shodan', 'spyse', 'sublist3r', 'threatcrowd',
        'trello', 'twitter', 'urlscan', 'virustotal', 'yahoo', 'zoomeye'
    ]

    def __init__(self, tool_path: Optional[str] = None, **kwargs):
        super().__init__(tool_path=tool_path, **kwargs)

        # theHarvester specific configuration
        self.default_sources = self.config.get('default_sources', ['google', 'bing', 'duckduckgo'])
        self.limit = self.config.get('limit', 500)
        self.delay = self.config.get('delay', 1)
        self.use_shodan = self.config.get('use_shodan', False)
        self.shodan_key = self.config.get('shodan_api_key')

    def get_default_tool_path(self) -> str:
        """Get default theHarvester installation path"""
        # Check common installation paths
        common_paths = [
            'theHarvester',
            'python3 -m theHarvester',
            '/usr/bin/theHarvester',
            '/usr/local/bin/theHarvester',
            'python /opt/theHarvester/theHarvester.py'
        ]

        return 'theHarvester'  # Assume it's in PATH

    def check_availability(self) -> bool:
        """Check if theHarvester is available"""
        try:
            import subprocess
            result = subprocess.run(
                [self.tool_path, '-h'],
                capture_output=True,
                timeout=10,
                shell=True if 'python' in self.tool_path else False
            )
            return 'theHarvester' in result.stdout.decode().lower()
        except Exception as e:
            logger.warning(f"theHarvester availability check failed: {e}")
            return False

    def validate_target(self, target: str) -> bool:
        """Validate target domain for theHarvester"""
        if not super().validate_target(target):
            return False

        # theHarvester expects domain names
        target = target.strip().lower()

        # Remove protocol if present
        if target.startswith(('http://', 'https://')):
            target = target.split('://', 1)[1]

        # Remove path if present
        if '/' in target:
            target = target.split('/')[0]

        # Basic domain validation
        if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', target):
            return False

        return True

    async def gather_intelligence(self, target: str, sources: Optional[List[str]] = None, **kwargs) -> ConnectorResult:
        """Gather intelligence using theHarvester"""
        start_time = asyncio.get_event_loop().time()

        if not self.validate_target(target):
            return ConnectorResult(
                success=False,
                tool_name='theHarvester',
                target=target,
                emails=[],
                domains=[],
                additional_data={},
                error="Invalid target domain format"
            )

        # Clean target
        clean_target = self._clean_target(target)

        # Use provided sources or defaults
        if sources is None:
            sources = self.default_sources

        # Validate sources
        valid_sources = [s for s in sources if s in self.AVAILABLE_SOURCES]
        if not valid_sources:
            valid_sources = ['google', 'bing']  # Fallback

        try:
            # Run theHarvester with retry logic
            result = await self.execute_with_retry(
                self._run_theharvester,
                clean_target,
                valid_sources,
                **kwargs
            )

            execution_time = asyncio.get_event_loop().time() - start_time

            # Parse results
            emails = self.extract_emails_from_text(result['stdout'])
            domains = self.extract_domains_from_text(result['stdout'])

            # Extract additional data
            additional_data = self._parse_additional_data(result['stdout'])

            # Log successful operation
            self.log_operation(
                'gather_intelligence',
                clean_target,
                True,
                f"Found {len(emails)} emails, {len(domains)} domains using sources: {', '.join(valid_sources)}"
            )

            return ConnectorResult(
                success=True,
                tool_name='theHarvester',
                target=clean_target,
                emails=emails,
                domains=domains,
                additional_data=additional_data,
                execution_time=execution_time,
                raw_output=result['stdout']
            )

        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"theHarvester execution failed: {str(e)}"

            # Log failed operation
            self.log_operation('gather_intelligence', clean_target, False, error_msg)

            return ConnectorResult(
                success=False,
                tool_name='theHarvester',
                target=clean_target,
                emails=[],
                domains=[],
                additional_data={},
                error=error_msg,
                execution_time=execution_time
            )

    async def _run_theharvester(self, target: str, sources: List[str], **kwargs) -> Dict[str, Any]:
        """Execute theHarvester command"""

        # Build command
        command = [self.tool_path]

        # Add domain
        command.extend(['-d', target])

        # Add sources
        command.extend(['-b', ','.join(sources)])

        # Add limit
        command.extend(['-l', str(self.limit)])

        # Add delay if specified
        if self.delay > 0:
            command.extend(['--delay', str(self.delay)])

        # Add Shodan integration if configured
        if self.use_shodan and self.shodan_key:
            command.extend(['--shodan-key', self.shodan_key])

        # Add additional options from kwargs
        if kwargs.get('ports'):
            command.extend(['-p', str(kwargs['ports'])])

        if kwargs.get('take_over'):
            command.append('-t')

        if kwargs.get('dns_lookup'):
            command.append('-n')

        if kwargs.get('dns_brute'):
            command.append('-c')

        # Set format to JSON if available (newer versions)
        command.extend(['-f', 'json'])

        logger.info(f"Running theHarvester command: {' '.join(command)}")

        # Execute command
        result = await self.run_subprocess(command)

        if result['returncode'] != 0:
            raise NetworkError(f"theHarvester failed with exit code {result['returncode']}: {result['stderr']}")

        return result

    def _clean_target(self, target: str) -> str:
        """Clean and normalize target domain"""
        target = target.strip().lower()

        # Remove protocol
        if target.startswith(('http://', 'https://')):
            target = target.split('://', 1)[1]

        # Remove path
        if '/' in target:
            target = target.split('/')[0]

        # Remove port
        if ':' in target:
            target = target.split(':')[0]

        return target

    def _parse_additional_data(self, output: str) -> Dict[str, Any]:
        """Parse additional data from theHarvester output"""
        additional_data = {
            'subdomains': [],
            'hosts': [],
            'linkedin_profiles': [],
            'twitter_profiles': [],
            'interesting_urls': []
        }

        lines = output.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()

            # Detect sections
            if 'Hosts found:' in line or '[*] Hosts found:' in line:
                current_section = 'hosts'
                continue
            elif 'Emails found:' in line or '[*] Emails found:' in line:
                current_section = 'emails'
                continue
            elif 'LinkedIn profiles found:' in line:
                current_section = 'linkedin'
                continue
            elif 'Twitter profiles found:' in line:
                current_section = 'twitter'
                continue

            # Parse content based on section
            if current_section == 'hosts' and line and not line.startswith('['):
                if '.' in line:
                    additional_data['hosts'].append(line)
                    # Extract subdomains
                    if line.count('.') > 1:
                        additional_data['subdomains'].append(line)

            elif current_section == 'linkedin' and 'linkedin.com' in line.lower():
                additional_data['linkedin_profiles'].append(line)

            elif current_section == 'twitter' and 'twitter.com' in line.lower():
                additional_data['twitter_profiles'].append(line)

        # Try to parse JSON output if available
        try:
            if '{' in output and '}' in output:
                json_start = output.find('{')
                json_end = output.rfind('}') + 1
                json_data = json.loads(output[json_start:json_end])

                if isinstance(json_data, dict):
                    additional_data.update(json_data)
        except (json.JSONDecodeError, ValueError):
            pass  # JSON parsing failed, use regex parsing

        return additional_data

    async def search_emails_only(self, target: str, sources: Optional[List[str]] = None) -> List[str]:
        """Search for emails only (convenience method)"""
        result = await self.gather_intelligence(target, sources)
        return result.emails if result.success else []

    async def search_subdomains_only(self, target: str, sources: Optional[List[str]] = None) -> List[str]:
        """Search for subdomains only (convenience method)"""
        result = await self.gather_intelligence(target, sources)
        return result.additional_data.get('subdomains', []) if result.success else []

    def get_recommended_sources(self, target_type: str = 'general') -> List[str]:
        """Get recommended sources based on target type"""
        recommendations = {
            'general': ['google', 'bing', 'duckduckgo', 'yahoo'],
            'social': ['linkedin', 'twitter'],
            'technical': ['certspotter', 'crtsh', 'dnsdumpster', 'virustotal'],
            'comprehensive': ['google', 'bing', 'linkedin', 'certspotter', 'dnsdumpster', 'virustotal'],
            'fast': ['google', 'bing'],
            'deep': ['all']
        }

        return recommendations.get(target_type, recommendations['general'])