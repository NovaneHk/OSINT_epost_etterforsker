"""
NovaNexus Connector
Direct integration to push scored leads/contacts into the NovaNexus platform
via its REST API.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .base_connector import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)


class NovaNexusConnector(BaseConnector):
    """Push processed leads/contacts directly into NovaNexus."""

    def __init__(
        self,
        api_url: str = "",
        api_key: str = "",
        campaign_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.tool_name = "NovaNexus"
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.campaign_id = campaign_id

    def is_available(self) -> bool:
        return bool(self.api_url and self.api_key)

    def check_availability(self) -> bool:
        """BaseConnector abstract method — delegates to is_available."""
        return self.is_available()

    async def gather_intelligence(self, target: str, **kwargs) -> ConnectorResult:
        """BaseConnector abstract method — delegates to search."""
        return await self.search(target, **kwargs)

    async def search(self, target: str, search_type: str = "email", **kwargs) -> ConnectorResult:
        """No-op — NovaNexus is a push target, not a search source."""
        return ConnectorResult(
            success=False,
            tool_name=self.tool_name,
            target=target,
            emails=[],
            domains=[],
            additional_data={},
            error="NovaNexus is a push target; use import_leads() instead.",
        )

    async def import_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """
        Push a single lead dict to NovaNexus.
        Returns the API response JSON or an error dict.
        """
        if not self.is_available():
            return {"success": False, "error": "NovaNexus not configured (missing api_url/api_key)"}

        payload: Dict[str, Any] = {
            "email": lead.get("email", ""),
            "name": lead.get("name", ""),
            "first_name": lead.get("first_name", ""),
            "last_name": lead.get("last_name", ""),
            "company": lead.get("company", ""),
            "role": lead.get("role", ""),
            "phone": lead.get("phone", ""),
            "domain": lead.get("domain", ""),
            "linkedin_url": lead.get("linkedin_url", ""),
            "industry": lead.get("industry", ""),
            "location": lead.get("location", ""),
            "confidence_score": lead.get("confidence_score") or lead.get("overall_score") or 0,
            "source": "OSINT_B2B_System",
        }
        if self.campaign_id:
            payload["campaign_id"] = self.campaign_id

        try:
            result = await asyncio.to_thread(self._post, "/api/v1/leads", payload)
            return {"success": True, "novanexus_id": result.get("id"), "response": result}
        except Exception as exc:
            logger.exception("NovaNexus import_lead error")
            return {"success": False, "error": str(exc)}

    async def import_leads(
        self,
        leads: List[Dict[str, Any]],
        campaign_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Bulk-push a list of leads to NovaNexus.
        Returns a summary with per-lead success/failure.
        """
        if not self.is_available():
            return {"success": False, "error": "NovaNexus not configured"}

        if campaign_id:
            self.campaign_id = campaign_id

        results = await asyncio.gather(
            *[self.import_lead(lead) for lead in leads],
            return_exceptions=True,
        )

        successes = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failures = len(results) - successes

        return {
            "success": failures == 0,
            "total": len(leads),
            "pushed": successes,
            "failed": failures,
            "details": [
                r if isinstance(r, dict) else {"success": False, "error": str(r)}
                for r in results
            ],
        }

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous HTTP POST (called via asyncio.to_thread)."""
        import urllib.request
        import json as _json

        data = _json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.api_url}{path}",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "OSINT-B2B-NovaNexus-Connector/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return _json.loads(resp.read().decode())
