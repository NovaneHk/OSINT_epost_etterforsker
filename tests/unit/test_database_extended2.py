"""Extended tests for core/database.py - covers remaining 60 uncovered lines."""

import gc
import json
import sqlite3
import pytest
import tempfile
import shutil
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.database import DatabaseManager, Contact, ContactStatus, AuditEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_db_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    gc.collect()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def db_manager(temp_db_dir):
    db_path = Path(temp_db_dir) / "test.db"
    mgr = DatabaseManager(str(db_path))
    yield mgr
    mgr.close()


# ---------------------------------------------------------------------------
# Contact: uncovered branches (lines 69-70, 86, 89-90)
# ---------------------------------------------------------------------------

class TestContactUncoveredBranches:
    def test_invalid_status_string_falls_back_to_unvalidated(self):
        """Lines 69-70: ContactStatus('garbage') raises ValueError → UNVALIDATED."""
        c = Contact(email="x@y.com", domain="y.com", status="COMPLETELY_INVALID_STATUS")
        assert c.status == ContactStatus.UNVALIDATED

    def test_from_dict_datetime_value_returned_directly(self):
        """Line 86: parse_dt() returns val directly when isinstance(val, datetime)."""
        from datetime import datetime
        dt = datetime(2024, 3, 15, 9, 0, 0)
        c = Contact.from_dict({
            "email": "test@co.com",
            "extracted_at": dt,   # already a datetime → line 86
        })
        assert c.extracted_at == dt

    def test_from_dict_unparseable_string_returns_none(self):
        """Lines 89-90: fromisoformat raises ValueError on garbage string → None.
        Use validated_at (not set to `now` by __post_init__) so None is preserved.
        """
        c = Contact.from_dict({
            "email": "test@co.com",
            "validated_at": "not-a-date",  # causes ValueError → parse_dt returns None
        })
        # validated_at is not auto-filled in __post_init__, so it stays None
        assert c.validated_at is None


# ---------------------------------------------------------------------------
# _connect: rollback on exception (lines 128-130)
# ---------------------------------------------------------------------------

class TestConnectRollback:
    def test_connect_rolls_back_and_reraises(self, db_manager):
        """Lines 128-130: exception inside _connect triggers rollback + re-raise."""
        with pytest.raises(RuntimeError, match="deliberate failure"):
            with db_manager._connect() as conn:
                conn.execute("SELECT 1")  # Valid query succeeds
                raise RuntimeError("deliberate failure")  # triggers rollback


# ---------------------------------------------------------------------------
# init_db (line 136)
# ---------------------------------------------------------------------------

class TestInitDb:
    def test_init_db_calls_init_database(self, db_manager):
        """Line 136: init_db() delegates to _init_database()."""
        with patch.object(db_manager, "_init_database") as mock_init:
            db_manager.init_db()
        mock_init.assert_called_once()


# ---------------------------------------------------------------------------
# _init_database: ALTER TABLE migrations (lines 257, 259, 261, 266)
# ---------------------------------------------------------------------------

class TestInitDatabaseMigrations:
    def test_alter_table_migrations_run_on_old_schema(self, temp_db_dir):
        """Lines 257, 259, 261, 266: ALTER TABLE runs when columns are missing."""
        db_path = Path(temp_db_dir) / "old_schema.db"

        # Pre-create ONLY the tables that need migration (with old schema).
        # Other tables (contacts, emails, seeds, leads, cache) are left for
        # _init_database to create fresh with the correct schema.
        conn = sqlite3.connect(str(db_path))
        conn.executescript("""
            PRAGMA journal_mode=DELETE;
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                domain TEXT
            );
        """)
        conn.commit()
        conn.close()

        # DatabaseManager.__init__ calls _init_database → migrations should run
        mgr = DatabaseManager(str(db_path))

        # Verify audit_log got new columns
        conn = sqlite3.connect(str(db_path))
        audit_cols = {row[1] for row in conn.execute("PRAGMA table_info(audit_log)").fetchall()}
        assert "entity_type" in audit_cols, "entity_type should have been added"
        assert "entity_id" in audit_cols, "entity_id should have been added"
        assert "user_id" in audit_cols, "user_id should have been added"

        # Verify companies got retrieved_at
        company_cols = {row[1] for row in conn.execute("PRAGMA table_info(companies)").fetchall()}
        assert "retrieved_at" in company_cols, "retrieved_at should have been added"

        conn.close()
        mgr.close()


# ---------------------------------------------------------------------------
# Exception handlers in DatabaseManager methods
# ---------------------------------------------------------------------------

class TestDatabaseManagerExceptionHandlers:
    """All the except blocks that are uncovered: trigger them by failing _connect."""

    def _break_connect(self, db_manager):
        """Context manager: make _connect raise RuntimeError."""
        return patch.object(db_manager, "_connect", side_effect=RuntimeError("DB exploded"))

    def test_add_contact_exception_returns_false(self, db_manager):
        """Lines 356-358: add_contact logs error and returns False on exception."""
        contact = Contact(email="test@x.com", domain="x.com")
        with self._break_connect(db_manager):
            result = db_manager.add_contact(contact)
        assert result is False

    def test_get_contact_exception_returns_none(self, db_manager):
        """Lines 373-374: get_contact logs error and returns None on exception."""
        with self._break_connect(db_manager):
            result = db_manager.get_contact("no@where.com")
        assert result is None

    def test_get_all_contacts_exception_returns_empty(self, db_manager):
        """Lines 390-392: get_all_contacts returns [] on exception."""
        with self._break_connect(db_manager):
            result = db_manager.get_all_contacts()
        assert result == []

    def test_update_contact_status_exception_returns_false(self, db_manager):
        """Lines 420-421: update_contact_status returns False on exception."""
        with self._break_connect(db_manager):
            result = db_manager.update_contact_status("no@x.com", ContactStatus.VALIDATED)
        assert result is False

    def test_get_contact_stats_exception_returns_zeros(self, db_manager):
        """Lines 449-451: get_contact_stats returns zero dict on exception."""
        with self._break_connect(db_manager):
            result = db_manager.get_contact_stats()
        assert result["total"] == 0
        assert result["validated"] == 0

    def test_get_contacts_by_status_exception_returns_empty(self, db_manager):
        """Lines 463-465: get_contacts_by_status returns [] on exception."""
        with self._break_connect(db_manager):
            result = db_manager.get_contacts_by_status(ContactStatus.VALIDATED)
        assert result == []

    def test_get_contacts_by_domain_exception_returns_empty(self, db_manager):
        """Lines 475-477: get_contacts_by_domain returns [] on exception."""
        with self._break_connect(db_manager):
            result = db_manager.get_contacts_by_domain("example.com")
        assert result == []

    def test_search_contacts_exception_returns_empty(self, db_manager):
        """Lines 491-493: search_contacts returns [] on exception."""
        with self._break_connect(db_manager):
            result = db_manager.search_contacts("query")
        assert result == []

    def test_add_audit_entry_exception_returns_false(self, db_manager):
        """Lines 513-515: add_audit_entry returns False on exception."""
        entry = AuditEntry(action="test", entity_type="contact", entity_id="x@y.com")
        with self._break_connect(db_manager):
            result = db_manager.add_audit_entry(entry)
        assert result is False

    def test_get_audit_entries_invalid_json_details(self, db_manager):
        """Lines 533-534: invalid JSON in details column → raw string used."""
        # Add a real audit entry with invalid JSON in details
        with db_manager._connect() as conn:
            conn.execute(
                "INSERT INTO audit_log (action, entity_type, entity_id, user_id, details) "
                "VALUES (?, ?, ?, ?, ?)",
                ("test_action", "contact", "a@b.com", "system", "NOT_VALID_JSON{{{")
            )

        entries = db_manager.get_audit_entries()
        # The entry with bad JSON gets details as the raw string
        bad_entry = next((e for e in entries if e.action == "test_action"), None)
        assert bad_entry is not None
        assert bad_entry.details == "NOT_VALID_JSON{{{"

    def test_get_audit_entries_exception_returns_empty(self, db_manager):
        """Lines 544-546: get_audit_entries returns [] on exception."""
        with self._break_connect(db_manager):
            result = db_manager.get_audit_entries()
        assert result == []

    def test_get_kpi_stats_exception_returns_zeros(self, db_manager):
        """Lines 588-590: get_kpi_stats returns zero dict on exception."""
        with self._break_connect(db_manager):
            result = db_manager.get_kpi_stats()
        assert result["leads7d"] == 0
        assert result["hits7d"] == 0

    def test_get_recent_leads_exception_returns_empty(self, db_manager):
        """Lines 631-633: get_recent_leads returns [] on exception."""
        with self._break_connect(db_manager):
            result = db_manager.get_recent_leads()
        assert result == []

    def test_cleanup_old_data_exception_returns_zeros(self, db_manager):
        """Lines 668-670: cleanup_old_data returns (0, 0) on exception."""
        with self._break_connect(db_manager):
            result = db_manager.cleanup_old_data()
        assert result == (0, 0)

    def test_log_audit_action_exception_logs_warning(self, db_manager):
        """Lines 853-854: _log_audit_action logs warning, doesn't raise."""
        with self._break_connect(db_manager), \
             patch("core.database.logger") as mock_log:
            db_manager._log_audit_action("x@y.com", "test_action")
        mock_log.warning.assert_called_once()

    def test_get_audit_log_exception_returns_empty(self, db_manager):
        """Lines 878-880: get_audit_log returns [] on exception."""
        with self._break_connect(db_manager):
            result = db_manager.get_audit_log()
        assert result == []


# ---------------------------------------------------------------------------
# close() exception handler and _get_connection (lines 1004-1005, 1014)
# ---------------------------------------------------------------------------

class TestCloseAndGetConnection:
    def test_close_suppresses_exception(self, db_manager):
        """Lines 1004-1005: close() silently swallows sqlite3 errors."""
        with patch("sqlite3.connect", side_effect=RuntimeError("can't connect")):
            db_manager.close()  # Must not raise

    def test_get_connection_returns_sqlite_connection(self, db_manager):
        """Line 1014: _get_connection() returns a real sqlite3.Connection."""
        conn = db_manager._get_connection()
        assert isinstance(conn, sqlite3.Connection)
        conn.close()
