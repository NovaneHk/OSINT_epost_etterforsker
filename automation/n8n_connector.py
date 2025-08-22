"""
n8n Connector for Workflow Automation
Provides integration with n8n for automated OSINT workflows
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import aiohttp

from core.error_handling import get_error_handler, NetworkError

logger = logging.getLogger(__name__)


class N8NConnector:
    """Connector for n8n workflow automation"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.error_handler = get_error_handler()

        # n8n configuration
        self.base_url = self.config.get('n8n_base_url', 'http://localhost:5678')
        self.webhook_url = self.config.get('webhook_url')
        self.api_key = self.config.get('api_key')
        self.timeout = self.config.get('timeout', 30)

        # Session management
        self._session = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'OSINT-B2B-System'
            }

            if self.api_key:
                headers['X-N8N-API-KEY'] = self.api_key

            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )

        return self._session

    async def send_webhook(self, data: Dict[str, Any], webhook_id: Optional[str] = None) -> Dict[str, Any]:
        """Send data to n8n webhook"""
        if not self.webhook_url and not webhook_id:
            raise ValueError("Either webhook_url or webhook_id must be provided")

        # Build webhook URL
        if webhook_id:
            url = f"{self.base_url}/webhook/{webhook_id}"
        else:
            url = self.webhook_url

        session = await self.get_session()

        try:
            # Add metadata to payload
            payload = {
                'timestamp': datetime.now().isoformat(),
                'source': 'osint-b2b-system',
                'data': data
            }

            async with session.post(url, json=payload) as response:
                response.raise_for_status()

                if response.content_type == 'application/json':
                    result = await response.json()
                else:
                    result = {'text': await response.text()}

                logger.info(f"Successfully sent webhook to n8n: {webhook_id or 'custom'}")
                return result

        except Exception as e:
            error_msg = f"Failed to send webhook: {e}"
            logger.error(error_msg)
            self.error_handler.handle_error(NetworkError(error_msg), {'webhook_url': url})
            raise NetworkError(error_msg)

    async def trigger_workflow(self, workflow_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger a specific n8n workflow"""
        url = f"{self.base_url}/webhook/osint-{workflow_name}"

        return await self.send_webhook(data, webhook_id=f"osint-{workflow_name}")

    async def send_intelligence_results(self, target: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Send intelligence gathering results to n8n"""
        workflow_data = {
            'type': 'intelligence_results',
            'target': target,
            'results': results,
            'summary': {
                'total_emails': len(results.get('emails', [])),
                'total_domains': len(results.get('domains', [])),
                'sources_used': list(results.get('sources', {}).keys()),
                'risk_level': self._calculate_risk_level(results)
            }
        }

        return await self.trigger_workflow('intelligence', workflow_data)

    async def send_breach_alerts(self, breached_emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send breach alert data to n8n"""
        workflow_data = {
            'type': 'breach_alert',
            'alert_level': 'high' if len(breached_emails) > 0 else 'low',
            'breached_emails': breached_emails,
            'summary': {
                'total_breached': len(breached_emails),
                'high_risk_count': len([e for e in breached_emails if e.get('risk_score', 0) > 0.7]),
                'sensitive_breaches': len([e for e in breached_emails if e.get('has_sensitive_breach', False)])
            }
        }

        return await self.trigger_workflow('breach-alert', workflow_data)

    async def send_campaign_data(self, campaign_id: str, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send campaign contact data to n8n"""
        workflow_data = {
            'type': 'campaign_data',
            'campaign_id': campaign_id,
            'contacts': contacts,
            'summary': {
                'total_contacts': len(contacts),
                'high_score_contacts': len([c for c in contacts if c.get('overall_score', 0) > 0.8]),
                'personas': list(set(c.get('persona_match') for c in contacts if c.get('persona_match')))
            }
        }

        return await self.trigger_workflow('campaign', workflow_data)

    async def request_manual_review(self, item_type: str, item_data: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Request manual review for suspicious or important items"""
        workflow_data = {
            'type': 'manual_review_request',
            'item_type': item_type,
            'item_data': item_data,
            'reason': reason,
            'priority': 'high' if 'sensitive' in reason.lower() or 'breach' in reason.lower() else 'medium',
            'requested_at': datetime.now().isoformat()
        }

        return await self.trigger_workflow('manual-review', workflow_data)

    async def send_system_health(self, health_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send system health data to n8n for monitoring"""
        workflow_data = {
            'type': 'system_health',
            'health_data': health_data,
            'status': health_data.get('overall_status', 'unknown'),
            'alert_level': self._get_health_alert_level(health_data)
        }

        return await self.trigger_workflow('health-monitor', workflow_data)

    async def get_workflow_status(self, execution_id: str) -> Dict[str, Any]:
        """Get status of a workflow execution"""
        if not self.api_key:
            raise ValueError("API key required for workflow status checks")

        url = f"{self.base_url}/api/v1/executions/{execution_id}"
        session = await self.get_session()

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to get workflow status: {e}")
            raise NetworkError(f"Failed to get workflow status: {e}")

    async def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get list of active workflows"""
        if not self.api_key:
            raise ValueError("API key required for workflow listing")

        url = f"{self.base_url}/api/v1/workflows"
        session = await self.get_session()

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                result = await response.json()
                return result.get('data', [])
        except Exception as e:
            logger.error(f"Failed to get active workflows: {e}")
            raise NetworkError(f"Failed to get active workflows: {e}")

    def _calculate_risk_level(self, results: Dict[str, Any]) -> str:
        """Calculate overall risk level from intelligence results"""
        risk_score = 0

        # Check for breaches
        breach_data = results.get('hibp_data', {})
        if breach_data.get('breach_count', 0) > 0:
            risk_score += 0.4

        if breach_data.get('sensitive_breaches'):
            risk_score += 0.3

        # Check for suspicious domains
        domains = results.get('domains', [])
        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf']
        if any(domain.endswith(tld) for domain in domains for tld in suspicious_tlds):
            risk_score += 0.2

        # Check for high volume of emails (potential spam)
        email_count = len(results.get('emails', []))
        if email_count > 100:
            risk_score += 0.1

        # Convert to risk level
        if risk_score >= 0.7:
            return 'high'
        elif risk_score >= 0.4:
            return 'medium'
        else:
            return 'low'

    def _get_health_alert_level(self, health_data: Dict[str, Any]) -> str:
        """Get alert level based on health data"""
        status = health_data.get('overall_status', 'unknown')

        if status == 'error':
            return 'critical'
        elif status == 'warning':
            return 'high'
        elif status == 'healthy':
            return 'low'
        else:
            return 'medium'

    async def create_workflow_templates(self) -> Dict[str, Any]:
        """Create standard workflow templates for OSINT operations"""
        templates = {
            'intelligence_workflow': {
                'name': 'OSINT Intelligence Processing',
                'description': 'Process and distribute intelligence gathering results',
                'webhook_path': 'osint-intelligence',
                'steps': [
                    'Receive intelligence data',
                    'Validate and enrich data',
                    'Apply business rules',
                    'Route to appropriate systems',
                    'Send notifications'
                ]
            },
            'breach_alert_workflow': {
                'name': 'Breach Alert Processing',
                'description': 'Handle breach alerts and notifications',
                'webhook_path': 'osint-breach-alert',
                'steps': [
                    'Receive breach data',
                    'Assess risk level',
                    'Generate alerts',
                    'Notify stakeholders',
                    'Log for audit'
                ]
            },
            'campaign_workflow': {
                'name': 'Campaign Data Processing',
                'description': 'Process and import campaign contact data',
                'webhook_path': 'osint-campaign',
                'steps': [
                    'Receive contact data',
                    'Validate and score contacts',
                    'Import to CRM',
                    'Create email lists',
                    'Schedule campaigns'
                ]
            }
        }

        return templates

    async def cleanup(self):
        """Cleanup resources"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None


class N8NWorkflowBuilder:
    """Helper class for building n8n workflow configurations"""

    @staticmethod
    def create_osint_intelligence_workflow() -> Dict[str, Any]:
        """Create n8n workflow configuration for intelligence processing"""
        return {
            "name": "OSINT Intelligence Processing",
            "nodes": [
                {
                    "parameters": {
                        "httpMethod": "POST",
                        "path": "osint-intelligence",
                        "responseMode": "responseNode"
                    },
                    "type": "n8n-nodes-base.webhook",
                    "name": "Intelligence Webhook",
                    "position": [250, 300]
                },
                {
                    "parameters": {
                        "functionCode": """
// Process OSINT intelligence data
const data = $input.first().json.data;
const results = data.results;

// Extract key metrics
const summary = {
  target: data.target,
  total_emails: results.emails?.length || 0,
  total_domains: results.domains?.length || 0,
  risk_level: data.summary?.risk_level || 'low',
  sources_used: Object.keys(results.sources || {}),
  timestamp: new Date().toISOString()
};

// Determine next actions based on risk level
let actions = [];
if (summary.risk_level === 'high') {
  actions.push('immediate_review');
  actions.push('security_alert');
}
if (summary.total_emails > 50) {
  actions.push('bulk_validation');
}

return {
  summary,
  actions,
  raw_data: data
};
"""
                    },
                    "type": "n8n-nodes-base.function",
                    "name": "Process Intelligence",
                    "position": [450, 300]
                },
                {
                    "parameters": {
                        "conditions": {
                            "string": [
                                {
                                    "value1": "={{$json.summary.risk_level}}",
                                    "operation": "equal",
                                    "value2": "high"
                                }
                            ]
                        }
                    },
                    "type": "n8n-nodes-base.if",
                    "name": "High Risk Check",
                    "position": [650, 300]
                }
            ],
            "connections": {
                "Intelligence Webhook": {
                    "main": [
                        [{"node": "Process Intelligence", "type": "main", "index": 0}]
                    ]
                },
                "Process Intelligence": {
                    "main": [
                        [{"node": "High Risk Check", "type": "main", "index": 0}]
                    ]
                }
            }
        }

    @staticmethod
    def create_breach_alert_workflow() -> Dict[str, Any]:
        """Create n8n workflow configuration for breach alerts"""
        return {
            "name": "OSINT Breach Alert Processing",
            "nodes": [
                {
                    "parameters": {
                        "httpMethod": "POST",
                        "path": "osint-breach-alert"
                    },
                    "type": "n8n-nodes-base.webhook",
                    "name": "Breach Alert Webhook",
                    "position": [250, 300]
                },
                {
                    "parameters": {
                        "functionCode": """
// Process breach alert data
const data = $input.first().json.data;
const breachedEmails = data.breached_emails;

// Calculate severity
let severity = 'low';
const highRiskCount = breachedEmails.filter(e => e.risk_score > 0.7).length;
const sensitiveCount = breachedEmails.filter(e => e.has_sensitive_breach).length;

if (sensitiveCount > 0 || highRiskCount > 5) {
  severity = 'critical';
} else if (highRiskCount > 0 || breachedEmails.length > 10) {
  severity = 'high';
} else if (breachedEmails.length > 0) {
  severity = 'medium';
}

return {
  severity,
  total_breached: breachedEmails.length,
  high_risk_count: highRiskCount,
  sensitive_count: sensitiveCount,
  alert_message: `Breach Alert: ${breachedEmails.length} emails compromised (${highRiskCount} high-risk)`,
  breached_emails: breachedEmails
};
"""
                    },
                    "type": "n8n-nodes-base.function",
                    "name": "Process Alert",
                    "position": [450, 300]
                }
            ]
        }