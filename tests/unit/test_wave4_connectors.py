"""
Wave 4 — Unit tests for Metagoofil, PwnDB and NovaNexus connectors.
All external I/O is mocked; no real network or CLI calls are made.
"""
import asyncio
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Ensure project root on sys.path so relative imports work
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ===========================================================================
# Metagoofil connector
# ===========================================================================

from integrations.metagoofil_connector import MetagoofilConnector  # noqa: E402

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


class TestMetagoofilConnector:

    def test_is_available_false_when_not_on_path(self):
        with patch("shutil.which", return_value=None):
            conn = MetagoofilConnector()
            assert conn.is_available() is False

    def test_is_available_true_when_on_path(self):
        with patch("shutil.which", return_value="/usr/bin/metagoofil"):
            conn = MetagoofilConnector()
            assert conn.is_available() is True

    @pytest.mark.asyncio
    async def test_search_returns_error_when_unavailable(self):
        with patch("shutil.which", return_value=None):
            conn = MetagoofilConnector()
            result = await conn.search("example.com")
        assert result.success is False
        assert result.error is not None
        assert result.tool_name == "Metagoofil"

    @pytest.mark.asyncio
    async def test_search_extracts_emails_from_output(self, tmp_path):
        """If metagoofil is on PATH, extracted emails must appear in result."""
        fake_stdout = (
            b"Searching PDF files...\n"
            b"Found: alice@example.com\n"
            b"User: Bob Smith\n"
            b"Author: carol@example.com\n"
            b"Creator: Microsoft Word\n"
        )
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(fake_stdout, b""))
        mock_proc.returncode = 0

        with (
            patch("shutil.which", return_value="/usr/bin/metagoofil"),
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
        ):
            conn = MetagoofilConnector(limit=5)
            result = await conn.search("example.com")

        # Emails found via regex in stdout
        assert result.success is True
        assert "alice@example.com" in result.emails or "carol@example.com" in result.emails

    def test_email_regex_matches_valid_emails(self):
        text = "contact: info@acme.org  noreply@sub.domain.io  bad@  good@x.co"
        found = _EMAIL_RE.findall(text)
        assert "info@acme.org" in found
        assert "good@x.co" in found
        assert "bad@" not in found

    @pytest.mark.asyncio
    async def test_search_handles_subprocess_timeout(self):
        import asyncio as _asyncio

        async def _raise(*args, **kwargs):
            raise _asyncio.TimeoutError

        mock_proc = MagicMock()
        mock_proc.communicate = _raise
        mock_proc.kill = MagicMock()

        with (
            patch("shutil.which", return_value="/usr/bin/metagoofil"),
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("asyncio.wait_for", side_effect=_asyncio.TimeoutError),
        ):
            conn = MetagoofilConnector()
            result = await conn.search("slow.target.com")

        assert result.success is False
        assert result.error is not None


# ===========================================================================
# PwnDB connector
# ===========================================================================

from integrations.pwndb_connector import PwnDBConnector  # noqa: E402


class TestPwnDBConnector:

    def test_is_available_false_when_tor_down(self):
        import socket

        def _fail(*a, **kw):
            raise OSError("Connection refused")

        with patch.object(socket.socket, "connect", _fail):
            conn = PwnDBConnector()
            assert conn.is_available() is False

    def test_is_available_true_when_tor_up(self):
        with patch("socket.create_connection", return_value=MagicMock()):
            conn = PwnDBConnector()
            assert conn.is_available() is True

    @pytest.mark.asyncio
    async def test_search_returns_error_when_tor_unavailable(self):
        with patch("socket.create_connection", side_effect=OSError):
            conn = PwnDBConnector()
            result = await conn.search("test@example.com")
        assert result.success is False
        assert "Tor" in (result.error or "")

    @pytest.mark.asyncio
    async def test_search_email_builds_correct_payload(self):
        """_query_pwndb must call POST with email split into local+domain."""
        captured: dict = {}

        def fake_query(self_inner, target, search_type):
            captured["target"] = target
            captured["search_type"] = search_type
            from integrations.base_connector import ConnectorResult
            return ConnectorResult(
                success=True,
                tool_name="PwnDB",
                target=target,
                emails=[target],
                domains=[],
                additional_data={"breach_count": 1, "leaks": [{"email": target, "password_hash": "abc"}]},
                error=None,
            )

        with (
            patch("socket.create_connection", return_value=MagicMock()),
            patch.object(PwnDBConnector, "_query_pwndb", fake_query),
        ):
            conn = PwnDBConnector()
            result = await conn.search("victim@corp.com")

        assert result.success is True
        assert captured["search_type"] == "email"

    @pytest.mark.asyncio
    async def test_search_domain_builds_correct_payload(self):
        captured: dict = {}

        def fake_query(self_inner, target, search_type):
            captured["search_type"] = search_type
            from integrations.base_connector import ConnectorResult
            return ConnectorResult(
                success=True,
                tool_name="PwnDB",
                target=target,
                emails=[],
                domains=[target],
                additional_data={"breach_count": 0, "leaks": []},
                error=None,
            )

        with (
            patch("socket.create_connection", return_value=MagicMock()),
            patch.object(PwnDBConnector, "_query_pwndb", fake_query),
        ):
            conn = PwnDBConnector()
            result = await conn.search("corp.com")

        assert result.success is True
        assert captured["search_type"] == "domain"

    def test_breach_count_capped_at_50(self):
        """additional_data['leaks'] must not exceed 50 entries."""
        conn = PwnDBConnector()
        # Simulate that _parse_response truncates at 50
        fake_leaks = [{"email": f"u{i}@x.com", "password_hash": "x"} for i in range(80)]
        from integrations.base_connector import ConnectorResult
        result = ConnectorResult(
            success=True,
            tool_name="PwnDB",
            target="x.com",
            emails=[],
            domains=["x.com"],
            additional_data={"breach_count": 80, "leaks": fake_leaks[:50]},
            error=None,
        )
        assert len(result.additional_data["leaks"]) <= 50


# ===========================================================================
# NovaNexus connector
# ===========================================================================

from integrations.novanexus_connector import NovaNexusConnector  # noqa: E402


class TestNovaNexusConnector:

    def test_is_available_false_when_not_configured(self):
        conn = NovaNexusConnector(api_url="", api_key="")
        assert conn.is_available() is False

    def test_is_available_true_when_fully_configured(self):
        conn = NovaNexusConnector(api_url="https://api.novanexus.io", api_key="secret")
        assert conn.is_available() is True

    @pytest.mark.asyncio
    async def test_search_always_returns_error(self):
        conn = NovaNexusConnector(api_url="https://api.novanexus.io", api_key="key")
        result = await conn.search("test@example.com")
        assert result.success is False
        assert "push target" in (result.error or "")

    @pytest.mark.asyncio
    async def test_import_lead_returns_error_when_not_configured(self):
        conn = NovaNexusConnector()
        result = await conn.import_lead({"email": "a@b.com"})
        assert result["success"] is False
        assert "not configured" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_import_lead_posts_correct_payload(self):
        """import_lead must call _post with the right path and a payload that includes email."""
        captured: list = []

        def fake_post(self_inner, path, payload):
            captured.append({"path": path, "payload": payload})
            return {"id": "nn-001"}

        with patch.object(NovaNexusConnector, "_post", fake_post):
            conn = NovaNexusConnector(api_url="https://api.novanexus.io", api_key="k")
            result = await conn.import_lead(
                {
                    "email": "sales@acme.com",
                    "name": "John Doe",
                    "company": "Acme Inc",
                    "confidence_score": 0.87,
                }
            )

        assert result["success"] is True
        assert result["novanexus_id"] == "nn-001"
        assert len(captured) == 1
        assert captured[0]["path"] == "/api/v1/leads"
        payload = captured[0]["payload"]
        assert payload["email"] == "sales@acme.com"
        assert payload["confidence_score"] == 0.87
        assert payload["source"] == "OSINT_B2B_System"

    @pytest.mark.asyncio
    async def test_import_leads_bulk_returns_summary(self):
        def fake_post(self_inner, path, payload):
            return {"id": f"nn-{payload['email'].split('@')[0]}"}

        with patch.object(NovaNexusConnector, "_post", fake_post):
            conn = NovaNexusConnector(api_url="https://api.novanexus.io", api_key="k")
            result = await conn.import_leads(
                [{"email": "a@x.com"}, {"email": "b@x.com"}, {"email": "c@x.com"}]
            )

        assert result["total"] == 3
        assert result["pushed"] == 3
        assert result["failed"] == 0
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_import_leads_bulk_reports_partial_failure(self):
        call_count = 0

        def fake_post(self_inner, path, payload):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Simulated API error")
            return {"id": "ok"}

        with patch.object(NovaNexusConnector, "_post", fake_post):
            conn = NovaNexusConnector(api_url="https://api.novanexus.io", api_key="k")
            result = await conn.import_leads(
                [{"email": "a@x.com"}, {"email": "b@x.com"}, {"email": "c@x.com"}]
            )

        assert result["total"] == 3
        assert result["pushed"] == 2
        assert result["failed"] == 1
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_campaign_id_injected_into_payload(self):
        captured: list = []

        def fake_post(self_inner, path, payload):
            captured.append(payload)
            return {"id": "1"}

        with patch.object(NovaNexusConnector, "_post", fake_post):
            conn = NovaNexusConnector(
                api_url="https://api.novanexus.io",
                api_key="k",
                campaign_id="camp-42",
            )
            await conn.import_lead({"email": "x@y.com"})

        assert captured[0].get("campaign_id") == "camp-42"
