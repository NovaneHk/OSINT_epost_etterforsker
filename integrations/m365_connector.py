"""Microsoft 365 connector using Microsoft Graph API (OAuth2 client-credentials)."""

import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"


class M365Connector:
    """Manage contacts in Microsoft 365 via Graph API."""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[str] = None

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _get_token(self) -> str:
        """Obtain an OAuth2 access token via client-credentials for Graph API."""
        resp = requests.post(
            _TOKEN_URL_TEMPLATE.format(tenant_id=self.tenant_id),
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
            },
            timeout=15,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def _headers(self) -> Dict[str, str]:
        if not self._token:
            self._get_token()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Look up an AAD user by email address."""
        resp = requests.get(
            f"{_GRAPH_BASE}/users",
            params={"$filter": f"mail eq '{email}'", "$select": "id,displayName,mail"},
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        values = resp.json().get("value", [])
        return values[0] if values else None

    def add_contact(self, display_name: str, email: str, company: str = "") -> str:
        """Create a personal contact (in the service account's People). Returns contact ID."""
        resp = requests.post(
            f"{_GRAPH_BASE}/me/contacts",
            json={
                "displayName": display_name,
                "emailAddresses": [{"address": email, "name": display_name}],
                "companyName": company,
            },
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("id", "")

    def add_or_update_contact(self, lead: Dict[str, Any]) -> str:
        """Upsert a lead as a personal M365 contact. Returns contact ID."""
        name = lead.get("name") or lead.get("email", "")
        email = lead.get("email", "")
        company = lead.get("company") or ""
        return self.add_contact(display_name=name, email=email, company=company)
