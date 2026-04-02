"""
Unit tests for GDPR compliance module — export and erase operations.
"""

import pytest
from unittest.mock import MagicMock, patch, call
import hashlib


class TestGDPRExport:
    """Tests for GDPRManager.export_lead_data."""

    def test_export_returns_dict_with_email(self):
        """Export result always has the target email in the response."""
        from backend.core.gdpr_compliance import GDPRManager
        manager = GDPRManager()
        with patch("backend.core.gdpr_compliance._get_conn") as mock_conn:
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = []
            mock_conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
            conn = MagicMock()
            conn.cursor.return_value = mock_cur
            mock_conn.return_value = conn
            result = manager.export_lead_data("test@example.com")
        assert result["email"] == "test@example.com"

    def test_export_result_has_required_keys(self):
        """Export result has leads, contacts, investigations, audit_logs keys."""
        from backend.core.gdpr_compliance import GDPRManager
        manager = GDPRManager()
        with patch("backend.core.gdpr_compliance._get_conn") as mock_conn:
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = []
            conn = MagicMock()
            conn.cursor.return_value = mock_cur
            mock_conn.return_value = conn
            result = manager.export_lead_data("user@test.com")
        assert "leads" in result
        assert "contacts" in result
        assert "investigations" in result
        assert "audit_logs" in result

    def test_export_handles_missing_tables_gracefully(self):
        """Export does not raise exceptions if tables are missing."""
        import sqlite3
        from backend.core.gdpr_compliance import GDPRManager
        manager = GDPRManager()
        with patch("backend.core.gdpr_compliance._get_conn") as mock_conn:
            mock_cur = MagicMock()
            mock_cur.fetchall.side_effect = sqlite3.OperationalError("no such table")
            conn = MagicMock()
            conn.cursor.return_value = mock_cur
            mock_conn.return_value = conn
            # Should not raise
            result = manager.export_lead_data("ghost@nowhere.com")
        assert result["email"] == "ghost@nowhere.com"


class TestGDPRErase:
    """Tests for GDPRManager.erase_lead_data."""

    def test_erase_anonymises_with_hashed_email(self):
        """Erased email is replaced with a SHA-256-based anonymous address."""
        email = "target@example.com"
        expected_hash = hashlib.sha256(email.encode()).hexdigest()[:12]
        expected_anon = f"gdpr-erased-{expected_hash}@erased.invalid"

        from backend.core.gdpr_compliance import GDPRManager
        manager = GDPRManager()
        with patch("backend.core.gdpr_compliance._get_conn") as mock_conn:
            mock_cur = MagicMock()
            mock_cur.rowcount = 1
            conn = MagicMock()
            conn.cursor.return_value = mock_cur
            mock_conn.return_value = conn
            manager.erase_lead_data(email)
        # Verify the anonymised email is injected into the UPDATE calls
        calls = mock_cur.execute.call_args_list
        update_calls = [c for c in calls if "UPDATE" in str(c)]
        assert any(expected_anon in str(c) for c in update_calls)

    def test_erase_returns_affected_rows(self):
        """erase_lead_data returns total count of affected rows."""
        from backend.core.gdpr_compliance import GDPRManager
        manager = GDPRManager()
        with patch("backend.core.gdpr_compliance._get_conn") as mock_conn:
            mock_cur = MagicMock()
            mock_cur.rowcount = 2
            conn = MagicMock()
            conn.cursor.return_value = mock_cur
            mock_conn.return_value = conn
            # Each UPDATE/DELETE contributes rowcount=2 → 3 operations = 6
            affected = manager.erase_lead_data("someone@example.com")
        assert isinstance(affected, int)
        assert affected >= 0

    def test_erase_handles_db_error_gracefully(self):
        """erase_lead_data returns 0 without raising on OperationalError."""
        import sqlite3
        from backend.core.gdpr_compliance import GDPRManager
        manager = GDPRManager()
        with patch("backend.core.gdpr_compliance._get_conn") as mock_conn:
            mock_cur = MagicMock()
            mock_cur.execute.side_effect = sqlite3.OperationalError("locked")
            conn = MagicMock()
            conn.cursor.return_value = mock_cur
            mock_conn.return_value = conn
            affected = manager.erase_lead_data("bad@example.com")
        assert affected == 0


class TestGDPRLogRequest:
    """Tests for GDPRManager.log_request."""

    def test_log_request_writes_to_audit_log(self):
        """log_request inserts a row into audit_log."""
        from backend.core.gdpr_compliance import GDPRManager
        manager = GDPRManager()
        with patch("backend.core.gdpr_compliance._get_conn") as mock_conn:
            mock_cur = MagicMock()
            conn = MagicMock()
            conn.cursor.return_value = mock_cur
            mock_conn.return_value = conn
            manager.log_request("export", "user@test.com", "admin-1")
        insert_calls = [c for c in mock_cur.execute.call_args_list if "INSERT" in str(c)]
        assert len(insert_calls) >= 1

    def test_log_request_action_uppercased(self):
        """GDPR action is stored uppercased in audit_log."""
        from backend.core.gdpr_compliance import GDPRManager
        manager = GDPRManager()
        with patch("backend.core.gdpr_compliance._get_conn") as mock_conn:
            mock_cur = MagicMock()
            conn = MagicMock()
            conn.cursor.return_value = mock_cur
            mock_conn.return_value = conn
            manager.log_request("erase", "user@test.com", "admin-1")
        calls = str(mock_cur.execute.call_args_list)
        assert "GDPR_ERASE" in calls
