"""
IntelOwl Connector
Stub integration for IntelOwl threat intelligence platform.
Requires IntelOwl running (default: http://localhost:80) with a valid API token.
"""

import logging
from typing import Dict, List, Any, Optional

from .base_connector import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)


class IntelOwlConnector(BaseConnector):
    """Connector for IntelOwl threat intelligence platform (stub — requires IntelOwl installation)."""

    def __init__(
        self,
        api_url: str = "http://localhost:80",
        api_key: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.tool_name = "IntelOwl"
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key

    def is_available(self) -> bool:
        """Check whether IntelOwl API is reachable."""
        if not self.api_key:
            return False
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self.api_url}/api/auth/checktoken",
                headers={"Authorization": f"Token {self.api_key}"},
            )
            with urllib.request.urlopen(req, timeout=5):
                return True
        except Exception:
            return False

    async def search(self, target: str, search_type: str = "email", **kwargs) -> ConnectorResult:
        """Submit *target* as an observable to IntelOwl. Returns empty result if not available."""
        if not self.is_available():
            logger.warning("IntelOwl not available at %s — skipping", self.api_url)
            return ConnectorResult(
                success=False,
                tool_name=self.tool_name,
                target=target,
                emails=[],
                domains=[],
                additional_data={},
                error="IntelOwl not available",
            )

        try:
            import json
            import urllib.request

            observable_classification = "email" if "@" in target else "domain"
            payload = json.dumps({
                "observable_name": target,
                "observable_classification": observable_classification,
                "analyzers_requested": [],  # empty = run all enabled analyzers
                "tags_labels": ["osint"],
            }).encode()
            req = urllib.request.Request(
                f"{self.api_url}/api/analyze_observable",
                data=payload,
                headers={
                    "Authorization": f"Token {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())

            job_id = data.get("id", "")
            logger.info("IntelOwl job started: %s for %s", job_id, target)

            return ConnectorResult(
                success=True,
                tool_name=self.tool_name,
                target=target,
                emails=[target] if "@" in target else [],
                domains=[target] if "@" not in target else [],
                additional_data={"job_id": job_id},
            )
        except Exception as exc:
            logger.error("IntelOwl search failed: %s", exc)
            return ConnectorResult(
                success=False,
                tool_name=self.tool_name,
                target=target,
                emails=[],
                domains=[],
                additional_data={},
                error=str(exc),
            )
