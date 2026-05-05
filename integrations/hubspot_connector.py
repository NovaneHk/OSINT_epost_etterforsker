"""HubSpot CRM connector using private app access token."""

import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.hubapi.com"


class HubSpotConnector:
    """Create and update HubSpot contacts."""

    def __init__(self, access_token: str):
        self.access_token = access_token

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Search for a contact by email. Returns HubSpot contact dict or None."""
        resp = requests.post(
            f"{_BASE_URL}/crm/v3/objects/contacts/search",
            json={
                "filterGroups": [
                    {
                        "filters": [
                            {"propertyName": "email", "operator": "EQ", "value": email}
                        ]
                    }
                ],
                "limit": 1,
            },
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0] if results else None

    def create_contact(self, email: str, firstname: str = "", lastname: str = "", company: str = "") -> str:
        """Create a new contact. Returns HubSpot contact ID."""
        resp = requests.post(
            f"{_BASE_URL}/crm/v3/objects/contacts",
            json={
                "properties": {
                    "email": email,
                    "firstname": firstname,
                    "lastname": lastname,
                    "company": company,
                }
            },
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("id", "")

    def update_contact(self, contact_id: str, properties: Dict[str, Any]) -> None:
        """Update existing contact properties."""
        resp = requests.patch(
            f"{_BASE_URL}/crm/v3/objects/contacts/{contact_id}",
            json={"properties": properties},
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()

    def create_or_update_contact(self, lead: Dict[str, Any]) -> str:
        """Upsert a lead as a HubSpot contact. Returns contact ID."""
        email = lead.get("email", "")
        name_parts = (lead.get("name") or "").split(maxsplit=1)
        firstname = name_parts[0] if name_parts else ""
        lastname = name_parts[1] if len(name_parts) > 1 else ""

        existing = self.find_by_email(email)
        if existing:
            contact_id = existing["id"]
            self.update_contact(contact_id, {
                "firstname": firstname,
                "lastname": lastname,
                "company": lead.get("company") or "",
                "jobtitle": lead.get("job_title") or "",
                "phone": lead.get("phone") or "",
            })
            return contact_id
        return self.create_contact(
            email=email,
            firstname=firstname,
            lastname=lastname,
            company=lead.get("company") or "",
        )
