"""
Base Connector for OSINT Tool Integrations
Provides common interface and functionality for all external tool connectors
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import json
import subprocess
import tempfile
import os
from pathlib import Path

from core.error_handling import get_error_handler, NetworkError, ValidationError

logger = logging.getLogger(__name__)


@dataclass
class ConnectorResult:
    """Standardized result from connector operations"""
    success: bool
    tool_name: str
    target: str
    emails: List[str]
    domains: List[str]
    additional_data: Dict[str, Any]
    error: Optional[str] = None
    execution_time: Optional[float] = None
    raw_output: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization"""
        return {
            'success': self.success,
            'tool_name': self.tool_name,
            'target': self.target,
            'emails': self.emails,
            'domains': self.domains,
            'additional_data': self.additional_data,
            'error': self.error,
            'execution_time': self.execution_time,
            'timestamp': datetime.now().isoformat()
        }


class BaseConnector(ABC):
    """Base class for all OSINT tool connectors"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.error_handler = get_error_handler()
        self.tool_name = self.__class__.__name__.replace('Connector', '')

        # Common configuration
        self.timeout = self.config.get('timeout', 300)  # 5 minutes default
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 5)

    @abstractmethod
    def check_availability(self) -> bool:
        """Check if the external tool is available and configured properly"""
        pass

    @abstractmethod
    async def gather_intelligence(self, target: str, **kwargs) -> ConnectorResult:
        """Gather intelligence for the specified target"""
        pass

    def validate_config(self) -> bool:
        """Default config validator used by connector manager."""
        return True

    def validate_target(self, target: str) -> bool:
        """Validate target format (domain, email, etc.)"""
        if not target or not isinstance(target, str):
            return False

        # Basic validation - override in subclasses for specific requirements
        target = target.strip()
        if not target:
            return False

        # Check for basic domain format
        if '.' in target and len(target.split('.')) >= 2:
            return True

        return False

    async def execute_with_retry(self, func, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed for {self.tool_name}: {e}. Retrying in {self.retry_delay}s...")
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"All {self.max_retries} attempts failed for {self.tool_name}: {e}")

        raise last_error

    def extract_emails_from_text(self, text: str) -> List[str]:
        """Extract email addresses from text using regex"""
        import re

        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)

        # Remove duplicates and filter out common false positives
        unique_emails = list(set(emails))
        filtered_emails = []

        for email in unique_emails:
            # Filter out common false positives
            if not any(skip in email.lower() for skip in [
                'example.com', 'test.com', 'domain.com', 'email.com',
                'noreply', 'no-reply', 'donotreply'
            ]):
                filtered_emails.append(email.lower())

        return filtered_emails

    def extract_domains_from_text(self, text: str) -> List[str]:
        """Extract domain names from text"""
        import re

        domain_pattern = r'\b[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        domains = re.findall(domain_pattern, text)

        # Filter and clean domains
        unique_domains = list(set(domains))
        filtered_domains = []

        for domain in unique_domains:
            domain = domain.lower().strip('.')
            # Basic domain validation
            if '.' in domain and len(domain.split('.')) >= 2 and not domain.startswith('.'):
                filtered_domains.append(domain)

        return filtered_domains

    async def run_subprocess(self, command: List[str], input_data: Optional[str] = None) -> Dict[str, Any]:
        """Run subprocess command asynchronously with timeout"""
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if input_data else None
            )

            # Run with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=input_data.encode() if input_data else None),
                timeout=self.timeout
            )

            return {
                'returncode': process.returncode,
                'stdout': stdout.decode('utf-8', errors='ignore'),
                'stderr': stderr.decode('utf-8', errors='ignore')
            }

        except asyncio.TimeoutError:
            logger.error(f"Command timed out after {self.timeout}s: {' '.join(command)}")
            raise NetworkError(f"Command timeout after {self.timeout}s")
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise NetworkError(f"Command execution failed: {e}")

    def create_temp_config(self, config_content: str) -> str:
        """Create temporary configuration file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf') as f:
            f.write(config_content)
            return f.name

    def cleanup_temp_file(self, file_path: str):
        """Clean up temporary file"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {file_path}: {e}")

    def log_operation(self, operation: str, target: str, success: bool, details: str = ""):
        """Log connector operation for audit purposes"""
        log_data = {
            'tool': self.tool_name,
            'operation': operation,
            'target': target,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }

        if success:
            logger.info(f"[{self.tool_name}] {operation} successful for {target}")
        else:
            logger.error(f"[{self.tool_name}] {operation} failed for {target}: {details}")

        # Store in error handler for tracking
        self.error_handler.log_connector_operation(log_data)


class CLIConnector(BaseConnector):
    """Base class for connectors that use command-line tools"""

    def __init__(self, tool_path: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.tool_path = tool_path or self.get_default_tool_path()

    @abstractmethod
    def get_default_tool_path(self) -> str:
        """Get default path for the command-line tool"""
        pass

    def check_availability(self) -> bool:
        """Check if the CLI tool is available"""
        try:
            # Try to run the tool with --help or --version
            result = subprocess.run(
                [self.tool_path, '--help'],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False


class APIConnector(BaseConnector):
    """Base class for connectors that use web APIs"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.base_url = base_url
        self.session = None

    async def get_session(self):
        """Get or create aiohttp session"""
        if self.session is None:
            import aiohttp
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=self.get_default_headers()
            )
        return self.session

    def get_default_headers(self) -> Dict[str, str]:
        """Get default HTTP headers"""
        headers = {
            'User-Agent': f'OSINT-B2B-System/{self.tool_name}',
            'Accept': 'application/json'
        }

        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        return headers

    async def make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        session = await self.get_session()

        try:
            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()

                if response.content_type == 'application/json':
                    return await response.json()
                else:
                    text = await response.text()
                    return {'text': text}

        except Exception as e:
            logger.error(f"API request failed: {e}")
            raise NetworkError(f"API request failed: {e}")

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None

    def check_availability(self) -> bool:
        """Check if API is configured and accessible"""
        return bool(self.api_key and self.base_url)