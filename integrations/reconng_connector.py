"""
Recon-ng Connector
Stub integration for Recon-ng OSINT reconnaissance framework.
Requires Recon-ng installed and accessible on PATH.
"""

import asyncio
import logging
import shutil
from typing import Dict, List, Any, Optional

from .base_connector import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)


class ReconNGConnector(BaseConnector):
    """Connector for Recon-ng OSINT framework (stub — requires Recon-ng installation)."""

    def __init__(self, workspace: str = "osint_default", **kwargs):
        super().__init__(**kwargs)
        self.tool_name = "ReconNG"
        self.workspace = workspace

    def is_available(self) -> bool:
        """Check whether recon-ng binary is on PATH."""
        return shutil.which("recon-ng") is not None

    async def search(self, target: str, search_type: str = "email", **kwargs) -> ConnectorResult:
        """Run recon-ng modules against *target*. Returns empty result if not available."""
        if not self.is_available():
            logger.warning("recon-ng not found on PATH — skipping")
            return ConnectorResult(
                success=False,
                tool_name=self.tool_name,
                target=target,
                emails=[],
                domains=[],
                additional_data={},
                error="recon-ng not installed",
            )

        try:
            # Build a minimal recon-ng resource script with multiple modules
            script = (
                f"workspaces create {self.workspace}\n"
                f"db insert domains domain={target}\n"
                "modules load recon/domains-contacts/whois_pocs\n"
                "run\n"
                "modules load recon/domains-contacts/pgp_search\n"
                "run\n"
                "exit\n"
            )

            proc = await asyncio.create_subprocess_exec(
                "recon-ng",
                "--no-version",
                "--no-check",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(script.encode()),
                timeout=self.timeout,
            )

            import re as _re
            output = stdout.decode(errors="replace")
            # Extract email-like tokens: word@word.tld, [word@word.tld], <word@word.tld>
            raw_emails = _re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", output)
            emails = list(dict.fromkeys(e.lower() for e in raw_emails))  # deduplicate, preserve order

            return ConnectorResult(
                success=True,
                tool_name=self.tool_name,
                target=target,
                emails=emails,
                domains=[target],
                additional_data={"raw_output_lines": len(output.splitlines())},
            )
        except asyncio.TimeoutError:
            return ConnectorResult(
                success=False,
                tool_name=self.tool_name,
                target=target,
                emails=[],
                domains=[],
                additional_data={},
                error="recon-ng timed out",
            )
        except Exception as exc:
            logger.error("ReconNG search failed: %s", exc)
            return ConnectorResult(
                success=False,
                tool_name=self.tool_name,
                target=target,
                emails=[],
                domains=[],
                additional_data={},
                error=str(exc),
            )
