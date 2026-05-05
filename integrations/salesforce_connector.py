"""Salesforce CRM connector using OAuth2 client-credentials flow."""

import logging
import re
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class SalesforceConnector:
    """Push leads to Salesforce via REST API."""

    def __init__(self, instance_url: str, client_id: str, client_secret: str):
        self.instance_url = instance_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[str] = None

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _authenticate(self) -> str:
        """Get OAuth2 access token via client-credentials flow."""
        resp = requests.post(
            f"{self.instance_url}/services/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=15,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def _headers(self) -> Dict[str, str]:
        if not self._token:
            self._authenticate()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def push_lead(self, lead: Dict[str, Any]) -> str:
        """Create or upsert a Lead record. Returns the Salesforce ID."""
        payload = {
            "LastName": (lead.get("name") or lead.get("email", "")).split()[-1] or "Unknown",
            "FirstName": (lead.get("name") or "").split()[0] if lead.get("name") else None,
            "Email": lead.get("email"),
            "Company": lead.get("company") or "Unknown",
            "Title": lead.get("job_title"),
            "Phone": lead.get("phone"),
            "Website": lead.get("website"),
            "Industry": lead.get("industry"),
            "LeadSource": "OSINT Etterforsker",
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        resp = requests.post(
            f"{self.instance_url}/services/data/v57.0/sobjects/Lead/",
            json=payload,
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("id", "")

    def search_contact(self, email: str) -> Optional[Dict[str, Any]]:
        """Find an existing Lead/Contact by email via SOQL."""
        safe_email = re.sub(r"[^a-zA-Z0-9.@_\-]", "", email)
        query = "SELECT Id, Name, Email, Company FROM Lead WHERE Email = '{}' LIMIT 1".format(safe_email)
        resp = requests.get(
            f"{self.instance_url}/services/data/v57.0/query",
            params={"q": query},
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        records = resp.json().get("records", [])
        return records[0] if records else None
