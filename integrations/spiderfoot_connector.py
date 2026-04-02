"""
SpiderFoot Connector
Stub integration for SpiderFoot OSINT automation tool.
Requires SpiderFoot running at http://localhost:5001 (or configured api_url).
"""

import logging
from typing import Dict, List, Any, Optional

from .base_connector import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)


class SpiderFootConnector(BaseConnector):
    """Connector for SpiderFoot OSINT platform (stub — requires SpiderFoot installation)."""

    def __init__(self, api_url: str = "http://localhost:5001", api_key: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.tool_name = "SpiderFoot"
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.available = False  # Will be set True after successful connection check

    def is_available(self) -> bool:
        """Check whether SpiderFoot API is reachable."""
        try:
            import urllib.request
            with urllib.request.urlopen(f"{self.api_url}/api/v1/ping", timeout=5) as resp:
                self.available = resp.status == 200
        except Exception:
            self.available = False
        return self.available

    async def search(self, target: str, search_type: str = "email", **kwargs) -> ConnectorResult:
        """Run a SpiderFoot scan on *target*. Returns empty result if not available."""
        if not self.is_available():
            logger.warning("SpiderFoot is not available at %s — skipping", self.api_url)
            return ConnectorResult(
                success=False,
                tool_name=self.tool_name,
                target=target,
                emails=[],
                domains=[],
                additional_data={},
                error="SpiderFoot not available",
            )

        try:
            import json
            import urllib.request
            import urllib.parse

            payload = json.dumps({
                "scanname": f"osint_{target}",
                "scantarget": target,
                "usecase": "all",
            }).encode()
            _headers: dict = {"Content-Type": "application/json"}
            if self.api_key:
                _headers["X-SFAPI-TOKEN"] = self.api_key
            req = urllib.request.Request(
                f"{self.api_url}/api/v1/startscan",
                data=payload,
                headers=_headers,
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())

            scan_id = data.get("id", "")
            logger.info("SpiderFoot scan started: %s", scan_id)

            # Poll for email results (up to 120 seconds, every 10s)
            emails: List[str] = []
            import time
            deadline = time.time() + 120
            while time.time() < deadline:
                time.sleep(10)
                try:
                    with urllib.request.urlopen(
                        f"{self.api_url}/api/v1/scaneventresults/{scan_id}/EMAILADDR",
                        timeout=10,
                    ) as poll_resp:
                        poll_data = json.loads(poll_resp.read().decode())
                        emails = list({
                            item.get("data", "").strip().lower()
                            for item in (poll_data if isinstance(poll_data, list) else [])
                            if "@" in str(item.get("data", ""))
                        })
                    if emails:
                        logger.info("SpiderFoot found %d email(s) for %s", len(emails), target)
                        break
                except Exception as poll_exc:
                    logger.debug("SpiderFoot poll error: %s", poll_exc)

            return ConnectorResult(
                success=True,
                tool_name=self.tool_name,
                target=target,
                emails=emails,
                domains=[],
                additional_data={"scan_id": scan_id, "emails_found": len(emails)},
            )
        except Exception as exc:
            logger.error("SpiderFoot search failed: %s", exc)
            return ConnectorResult(
                success=False,
                tool_name=self.tool_name,
                target=target,
                emails=[],
                domains=[],
                additional_data={},
                error=str(exc),
            )
