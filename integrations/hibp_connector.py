"""
Have I Been Pwned (HIBP) Connector
Integration with HIBP API for checking email addresses against data breaches
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from .base_connector import APIConnector, ConnectorResult
from core.error_handling import NetworkError, ValidationError

logger = logging.getLogger(__name__)


class HIBPConnector(APIConnector):
    """Connector for Have I Been Pwned API integration"""

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(
            api_key=api_key,
            base_url='https://haveibeenpwned.com/api/v3',
            **kwargs
        )

        # HIBP specific configuration
        self.rate_limit_delay = self.config.get('rate_limit_delay', 1.5)  # HIBP requires 1.5s between requests
        self.include_unverified = self.config.get('include_unverified', False)
        self.truncate_response = self.config.get('truncate_response', False)

        # Track last request time for rate limiting
        self._last_request_time = 0

    def get_default_headers(self) -> Dict[str, str]:
        """Get default HTTP headers for HIBP API"""
        headers = super().get_default_headers()

        if self.api_key:
            headers['hibp-api-key'] = self.api_key

        headers['User-Agent'] = 'OSINT-B2B-System-HIBP-Connector'
        return headers

    def check_availability(self) -> bool:
        """Check if HIBP API is configured and accessible"""
        if not self.api_key:
            logger.warning("HIBP API key not configured")
            return False

        if not self.base_url:
            return False

        return True

    async def gather_intelligence(self, target: str, **kwargs) -> ConnectorResult:
        """Gather breach intelligence for email address"""
        start_time = asyncio.get_event_loop().time()

        if not self.validate_email(target):
            return ConnectorResult(
                success=False,
                tool_name='HIBP',
                target=target,
                emails=[],
                domains=[],
                additional_data={},
                error="Invalid email address format"
            )

        try:
            # Check breaches and pastes
            breach_data = await self.check_breaches(target)
            paste_data = await self.check_pastes(target)

            execution_time = asyncio.get_event_loop().time() - start_time

            # Determine if email was found in any breaches
            has_breaches = len(breach_data.get('breaches', [])) > 0
            has_pastes = len(paste_data.get('pastes', [])) > 0

            additional_data = {
                'breach_count': len(breach_data.get('breaches', [])),
                'paste_count': len(paste_data.get('pastes', [])),
                'breaches': breach_data.get('breaches', []),
                'pastes': paste_data.get('pastes', []),
                'risk_score': self._calculate_risk_score(breach_data, paste_data),
                'latest_breach': self._get_latest_breach(breach_data.get('breaches', [])),
                'sensitive_breaches': self._get_sensitive_breaches(breach_data.get('breaches', []))
            }

            # Log operation
            self.log_operation(
                'check_breaches',
                target,
                True,
                f"Found {additional_data['breach_count']} breaches, {additional_data['paste_count']} pastes"
            )

            return ConnectorResult(
                success=True,
                tool_name='HIBP',
                target=target,
                emails=[target] if (has_breaches or has_pastes) else [],
                domains=[],
                additional_data=additional_data,
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"HIBP check failed: {str(e)}"

            self.log_operation('check_breaches', target, False, error_msg)

            return ConnectorResult(
                success=False,
                tool_name='HIBP',
                target=target,
                emails=[],
                domains=[],
                additional_data={},
                error=error_msg,
                execution_time=execution_time
            )

    async def check_breaches(self, email: str) -> Dict[str, Any]:
        """Check email against HIBP breach database"""
        await self._enforce_rate_limit()

        url = f"{self.base_url}/breachedaccount/{email}"
        params = {}

        if self.include_unverified:
            params['includeUnverified'] = 'true'

        if self.truncate_response:
            params['truncateResponse'] = 'true'

        try:
            response = await self.make_request('GET', url, params=params)

            if isinstance(response, list):
                return {'breaches': response}
            else:
                return {'breaches': []}

        except Exception as e:
            if '404' in str(e):
                # No breaches found (normal case)
                return {'breaches': []}
            else:
                raise e

    async def check_pastes(self, email: str) -> Dict[str, Any]:
        """Check email against HIBP paste database"""
        await self._enforce_rate_limit()

        url = f"{self.base_url}/pasteaccount/{email}"

        try:
            response = await self.make_request('GET', url)

            if isinstance(response, list):
                return {'pastes': response}
            else:
                return {'pastes': []}

        except Exception as e:
            if '404' in str(e):
                # No pastes found (normal case)
                return {'pastes': []}
            else:
                raise e

    async def get_breach_details(self, breach_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific breach"""
        await self._enforce_rate_limit()

        url = f"{self.base_url}/breach/{breach_name}"

        try:
            response = await self.make_request('GET', url)
            return response if isinstance(response, dict) else {}
        except Exception as e:
            logger.warning(f"Failed to get breach details for {breach_name}: {e}")
            return {}

    async def get_all_breaches(self) -> List[Dict[str, Any]]:
        """Get list of all breaches in HIBP database"""
        await self._enforce_rate_limit()

        url = f"{self.base_url}/breaches"

        try:
            response = await self.make_request('GET', url)
            return response if isinstance(response, list) else []
        except Exception as e:
            logger.warning(f"Failed to get all breaches: {e}")
            return []

    async def check_multiple_emails(self, emails: List[str]) -> Dict[str, ConnectorResult]:
        """Check multiple emails for breaches (batch operation)"""
        results = {}

        for email in emails:
            try:
                result = await self.gather_intelligence(email)
                results[email] = result

                # Add extra delay for batch operations
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Failed to check {email}: {e}")
                results[email] = ConnectorResult(
                    success=False,
                    tool_name='HIBP',
                    target=email,
                    emails=[],
                    domains=[],
                    additional_data={},
                    error=str(e)
                )

        return results

    def validate_email(self, email: str) -> bool:
        """Validate email format for HIBP checking"""
        import re

        if not email or not isinstance(email, str):
            return False

        email = email.strip().lower()

        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))

    async def _enforce_rate_limit(self):
        """Enforce HIBP rate limiting"""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)

        self._last_request_time = asyncio.get_event_loop().time()

    def _calculate_risk_score(self, breach_data: Dict[str, Any], paste_data: Dict[str, Any]) -> float:
        """Calculate risk score based on breach and paste data"""
        breaches = breach_data.get('breaches', [])
        pastes = paste_data.get('pastes', [])

        score = 0.0

        # Base score for having any breaches
        if breaches:
            score += 0.3

        if pastes:
            score += 0.2

        # Additional score based on number of breaches
        score += min(len(breaches) * 0.1, 0.3)

        # Additional score for sensitive breaches
        for breach in breaches:
            if breach.get('IsSensitive', False):
                score += 0.1

            # Recent breaches are more concerning
            breach_date = breach.get('BreachDate', '')
            if breach_date:
                try:
                    breach_datetime = datetime.fromisoformat(breach_date.replace('Z', '+00:00'))
                    days_ago = (datetime.now() - breach_datetime.replace(tzinfo=None)).days
                    if days_ago < 365:  # Within last year
                        score += 0.1
                except:
                    pass

        # Cap score at 1.0
        return min(score, 1.0)

    def _get_latest_breach(self, breaches: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get the most recent breach"""
        if not breaches:
            return None

        latest = None
        latest_date = None

        for breach in breaches:
            breach_date = breach.get('BreachDate', '')
            if breach_date:
                try:
                    breach_datetime = datetime.fromisoformat(breach_date.replace('Z', '+00:00'))
                    if latest_date is None or breach_datetime > latest_date:
                        latest_date = breach_datetime
                        latest = breach
                except:
                    pass

        return latest

    def _get_sensitive_breaches(self, breaches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get list of sensitive breaches"""
        return [breach for breach in breaches if breach.get('IsSensitive', False)]

    def format_breach_summary(self, result: ConnectorResult) -> str:
        """Format breach data into human-readable summary"""
        if not result.success:
            return f"Error checking {result.target}: {result.error}"

        additional_data = result.additional_data
        breach_count = additional_data.get('breach_count', 0)
        paste_count = additional_data.get('paste_count', 0)
        risk_score = additional_data.get('risk_score', 0)

        if breach_count == 0 and paste_count == 0:
            return f"✅ {result.target}: No breaches found"

        summary = f"⚠️  {result.target}: {breach_count} breaches, {paste_count} pastes (Risk: {risk_score:.1f})"

        latest_breach = additional_data.get('latest_breach')
        if latest_breach:
            breach_name = latest_breach.get('Name', 'Unknown')
            breach_date = latest_breach.get('BreachDate', 'Unknown')
            summary += f"\n   Latest: {breach_name} ({breach_date})"

        sensitive_count = len(additional_data.get('sensitive_breaches', []))
        if sensitive_count > 0:
            summary += f"\n   ⚠️ {sensitive_count} sensitive breaches"

        return summary