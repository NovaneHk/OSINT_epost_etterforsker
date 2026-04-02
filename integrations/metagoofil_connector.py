"""
Metagoofil Connector
Integration with Metagoofil for extracting metadata (author, email, software)
from publicly accessible documents on a target domain.
Requires metagoofil installed: pip install metagoofil
"""

import asyncio
import logging
import shutil
import tempfile
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_connector import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


class MetagoofilConnector(BaseConnector):
    """Extract document metadata (emails, authors, software) via Metagoofil."""

    def __init__(
        self,
        filetypes: Optional[List[str]] = None,
        limit: int = 20,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.tool_name = "Metagoofil"
        self.filetypes = filetypes or ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx"]
        self.limit = limit

    def is_available(self) -> bool:
        """Check whether metagoofil is on PATH."""
        return shutil.which("metagoofil") is not None

    def check_availability(self) -> bool:
        """BaseConnector abstract method — delegates to is_available."""
        return self.is_available()

    async def gather_intelligence(self, target: str, **kwargs) -> ConnectorResult:
        """BaseConnector abstract method — delegates to search."""
        return await self.search(target, **kwargs)

    async def search(self, target: str, search_type: str = "domain", **kwargs) -> ConnectorResult:
        """
        Run metagoofil against *target* domain and extract emails + metadata
        from public documents.
        """
        if not self.is_available():
            logger.warning("metagoofil not found on PATH — skipping")
            return ConnectorResult(
                success=False,
                tool_name=self.tool_name,
                target=target,
                emails=[],
                domains=[],
                additional_data={},
                error="metagoofil not installed (pip install metagoofil)",
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                args = [
                    "metagoofil",
                    "-d", target,
                    "-t", ",".join(self.filetypes),
                    "-l", str(self.limit),
                    "-n", str(self.limit),
                    "-o", tmpdir,
                ]
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.timeout,
                )

                output = stdout.decode(errors="replace") + stderr.decode(errors="replace")

                # Extract emails from stdout
                raw_emails = _EMAIL_RE.findall(output)
                emails = list(dict.fromkeys(e.lower() for e in raw_emails))

                # Extract usernames / authors from "User:" lines
                authors = re.findall(r"(?:User|Author):\s*(.+)", output, re.IGNORECASE)
                software = re.findall(r"(?:Creator|Producer|Software):\s*(.+)", output, re.IGNORECASE)

                # Count downloaded files
                downloaded = list(Path(tmpdir).glob("*"))
                file_count = len(downloaded)

                return ConnectorResult(
                    success=True,
                    tool_name=self.tool_name,
                    target=target,
                    emails=emails,
                    domains=[target],
                    additional_data={
                        "authors": list(dict.fromkeys(a.strip() for a in authors)),
                        "software": list(dict.fromkeys(s.strip() for s in software)),
                        "filetypes_searched": self.filetypes,
                        "documents_downloaded": file_count,
                    },
                )

            except asyncio.TimeoutError:
                return ConnectorResult(
                    success=False,
                    tool_name=self.tool_name,
                    target=target,
                    emails=[],
                    domains=[],
                    additional_data={},
                    error=f"metagoofil timed out after {self.timeout}s",
                )
            except Exception as exc:
                logger.exception("Metagoofil error for %s", target)
                return ConnectorResult(
                    success=False,
                    tool_name=self.tool_name,
                    target=target,
                    emails=[],
                    domains=[],
                    additional_data={},
                    error=str(exc),
                )
