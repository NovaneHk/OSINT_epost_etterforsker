"""
PwnDB Connector
Check email addresses against PwnDB — a dark-web breach aggregator
accessible via Tor proxy (socks5h://127.0.0.1:9050).

When Tor is unavailable the connector returns a graceful failure result.
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

from .base_connector import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PWNDB_ONION = "pwndb2am4tzkvold.onion"


class PwnDBConnector(BaseConnector):
    """
    Query PwnDB for leaked credentials associated with an email address.

    Requires:
    - Tor running locally on port 9050 (socks5h proxy)
    - `requests[socks]` installed: pip install requests[socks]
    """

    def __init__(
        self,
        tor_proxy: str = "socks5h://127.0.0.1:9050",
        onion_host: str = _PWNDB_ONION,
        port: int = 80,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.tool_name = "PwnDB"
        self.tor_proxy = tor_proxy
        self.base_url = f"http://{onion_host}:{port}"

    def is_available(self) -> bool:
        """Check whether the Tor proxy is reachable."""
        try:
            import socket
            proxy_host, proxy_port = "127.0.0.1", 9050
            with socket.create_connection((proxy_host, proxy_port), timeout=3):
                return True
        except OSError:
            return False

    def check_availability(self) -> bool:
        """BaseConnector abstract method — delegates to is_available."""
        return self.is_available()

    async def gather_intelligence(self, target: str, **kwargs) -> ConnectorResult:
        """BaseConnector abstract method — delegates to search."""
        return await self.search(target, **kwargs)

    async def search(self, target: str, search_type: str = "auto", **kwargs) -> ConnectorResult:
        """Check *target* (email or domain) against PwnDB for leaked credentials.

        *search_type* is auto-detected from *target* when set to ``"auto"``
        (or when not provided): targets containing ``@`` are treated as emails,
        everything else as a domain.
        """
        if search_type == "auto":
            search_type = "email" if "@" in target else "domain"
        if not self.is_available():
            logger.warning("PwnDB: Tor proxy not reachable — skipping")
            return ConnectorResult(
                success=False,
                tool_name=self.tool_name,
                target=target,
                emails=[],
                domains=[],
                additional_data={},
                error="Tor proxy not available (start Tor on port 9050)",
            )

        try:
            result = await asyncio.to_thread(self._query_pwndb, target, search_type)
            return result
        except asyncio.TimeoutError:
            return ConnectorResult(
                success=False,
                tool_name=self.tool_name,
                target=target,
                emails=[],
                domains=[],
                additional_data={},
                error=f"PwnDB query timed out after {self.timeout}s",
            )
        except Exception as exc:
            logger.exception("PwnDB error for %s", target)
            return ConnectorResult(
                success=False,
                tool_name=self.tool_name,
                target=target,
                emails=[],
                domains=[],
                additional_data={},
                error=str(exc),
            )

    def _query_pwndb(self, target: str, search_type: str) -> ConnectorResult:
        """Synchronous PwnDB query (runs in thread via asyncio.to_thread)."""
        import requests  # type: ignore

        proxies = {"http": self.tor_proxy, "https": self.tor_proxy}

        if "@" in target:
            # Single email check
            local, domain = target.split("@", 1)
            payload = {"leak": {"email": local, "domain": domain}, "type": "leak"}
        else:
            # Domain-wide check
            payload = {"leak": {"domain": target}, "type": "leak"}

        resp = requests.post(
            f"{self.base_url}/",
            json=payload,
            proxies=proxies,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

        leaks: List[Dict[str, Any]] = data if isinstance(data, list) else []
        leaked_emails = list({
            f"{entry.get('email', '')}@{entry.get('domain', '')}"
            for entry in leaks
            if entry.get("email") and entry.get("domain")
        })

        return ConnectorResult(
            success=True,
            tool_name=self.tool_name,
            target=target,
            emails=leaked_emails,
            domains=[target] if "." in target else [],
            additional_data={
                "breach_count": len(leaks),
                "leaks": [
                    {
                        "email": f"{e.get('email', '')}@{e.get('domain', '')}",
                        "password_hash": e.get("password", "")[:8] + "***" if e.get("password") else None,
                    }
                    for e in leaks[:50]  # cap at 50 entries
                ],
            },
        )
