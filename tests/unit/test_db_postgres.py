"""Tests for core/db_postgres.py - PostgresDatabaseManager (0% → 100%)."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helper: build a fully mocked PostgresDatabaseManager without real DB
# ---------------------------------------------------------------------------

def _mock_engine_and_make_manager(
    tables=None,
    connect_raises=None,
):
    """
    Instantiate PostgresDatabaseManager with all SQLAlchemy pieces mocked.

    Parameters
    ----------
    tables        : list of table names returned by inspector (default: ['contacts'])
    connect_raises: exception to raise from engine.connect().__enter__().__execute(), or None
    """
    if tables is None:
        tables = ["contacts"]

    with patch("core.db_postgres.create_engine") as mock_create_engine, \
         patch("core.db_postgres.sessionmaker"), \
         patch("core.db_postgres.scoped_session") as mock_scoped_session, \
         patch("core.db_postgres.inspect") as mock_inspect, \
         patch("core.db_postgres.QueuePool"):

        # Engine + connection context manager
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn_ctx = MagicMock()
        mock_conn_ctx.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn_ctx.__exit__ = MagicMock(return_value=False)

        if connect_raises:
            mock_engine.connect.side_effect = connect_raises
        else:
            mock_engine.connect.return_value = mock_conn_ctx

        mock_create_engine.return_value = mock_engine

        # Inspector
        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = tables
        mock_inspect.return_value = mock_inspector

        # Session
        mock_session = MagicMock()
        mock_scoped_session.return_value = mock_session

        from core.db_postgres import PostgresDatabaseManager
        mgr = PostgresDatabaseManager("postgresql://user:pass@localhost/testdb")

    return mgr, mock_engine, mock_session


# ---------------------------------------------------------------------------
# __init__ + _verify_connection
# ---------------------------------------------------------------------------

class TestPostgresInit:
    def test_init_success_with_tables(self):
        """Happy path: engine created, connection OK, contacts table present."""
        mgr, engine, _ = _mock_engine_and_make_manager(tables=["contacts", "audit_log"])
        assert mgr.database_url == "postgresql://user:pass@localhost/testdb"

    def test_init_success_without_contacts_table_logs_warning(self):
        """_verify_connection warns when 'contacts' table is missing."""
        with patch("core.db_postgres.logger") as mock_log:
            _mock_engine_and_make_manager(tables=["other_table"])
        mock_log.warning.assert_called_once()
        assert "not found" in mock_log.warning.call_args[0][0].lower() or \
               "tables" in mock_log.warning.call_args[0][0].lower()

    def test_init_connect_exception_is_reraised(self):
        """_verify_connection logs error and re-raises connection exception."""
        with pytest.raises(RuntimeError, match="no DB"):
            with patch("core.db_postgres.create_engine") as mock_ce, \
                 patch("core.db_postgres.sessionmaker"), \
                 patch("core.db_postgres.scoped_session"), \
                 patch("core.db_postgres.inspect"), \
                 patch("core.db_postgres.QueuePool"), \
                 patch("core.db_postgres.logger") as mock_log:

                mock_engine = MagicMock()
                mock_engine.connect.side_effect = RuntimeError("no DB")
                mock_ce.return_value = mock_engine

                from core.db_postgres import PostgresDatabaseManager
                PostgresDatabaseManager("postgresql://user:pass@localhost/testdb")

        mock_log.error.assert_called_once()


# ---------------------------------------------------------------------------
# get_kpi_stats
# ---------------------------------------------------------------------------

class TestGetKpiStats:
    def _make_mgr_with_session(self, session_execute_values):
        """
        session_execute_values: list of scalar values to return for each execute().scalar() call.
        """
        mgr, _, mock_session_factory = _mock_engine_and_make_manager()

        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session

        # Configure scalar() return values in order
        scalars = iter(session_execute_values)
        mock_session.execute.return_value.scalar.side_effect = lambda: next(scalars)

        mgr.Session = mock_session_factory
        return mgr, mock_session

    def test_happy_path_all_queries_succeed(self):
        """get_kpi_stats returns correct dict when all queries return values."""
        # Five .scalar() calls: leads_7d, hits_7d, total, validated, exports_7d, total_sources
        mgr, mock_session = self._make_mgr_with_session([10, 5, 100, 20, 3, 7])

        result = mgr.get_kpi_stats()

        assert result["leads7d"] == 10
        assert result["hits7d"] == 5
        assert result["exports7d"] == 3
        assert result["total_sources"] == 7
        assert result["conversion_rate"] == pytest.approx(20.0, abs=0.1)
        mock_session.close.assert_called_once()

    def test_zero_total_contacts_avoids_division(self):
        """get_kpi_stats handles total=0 → conversion_rate stays 0.0."""
        # leads, hits, total=0, validated, exports, sources
        mgr, mock_session = self._make_mgr_with_session([0, 0, 0, 0, 0, 0])

        result = mgr.get_kpi_stats()

        assert result["conversion_rate"] == pytest.approx(0.0)

    def test_none_scalars_default_to_zero(self):
        """Scalar may return None → fallback to 0."""
        mgr, mock_session = self._make_mgr_with_session([None, None, None, None, None, None])

        result = mgr.get_kpi_stats()

        assert result["leads7d"] == 0
        assert result["hits7d"] == 0
        assert result["conversion_rate"] == pytest.approx(0.0)

    def test_exception_returns_zero_dict(self):
        """get_kpi_stats returns zero-filled dict on exception."""
        mgr, _, mock_session_factory = _mock_engine_and_make_manager()
        mock_session = MagicMock()
        mock_session.execute.side_effect = RuntimeError("DB down")
        mock_session_factory.return_value = mock_session
        mgr.Session = mock_session_factory

        result = mgr.get_kpi_stats()

        assert result["leads7d"] == 0
        assert result["hits7d"] == 0
        assert result["conversion_rate"] == 0.0
        assert result["exports7d"] == 0
        assert result["total_sources"] == 0
        mock_session.close.assert_called_once()


# ---------------------------------------------------------------------------
# get_recent_leads
# ---------------------------------------------------------------------------

class TestGetRecentLeads:
    def _make_mgr_with_rows(self, rows):
        mgr, _, mock_session_factory = _mock_engine_and_make_manager()

        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        mock_session.execute.return_value = iter(rows)

        mgr.Session = mock_session_factory
        return mgr, mock_session

    def _make_row(self, **kwargs):
        """Build a mock DB row with the expected attributes."""
        row = MagicMock()
        row.id = kwargs.get("id", 1)
        row.email = kwargs.get("email", "test@example.com")
        row.name = kwargs.get("name", "Test User")
        row.company = kwargs.get("company", "ACME")
        row.role = kwargs.get("role", "CTO")
        row.source = kwargs.get("source", "web")
        row.overall_score = kwargs.get("overall_score", 0.85)
        row.extracted_at = kwargs.get("extracted_at", datetime(2024, 1, 15, 12, 0, 0))
        # updated_at presence controlled by kwargs
        if "updated_at" in kwargs:
            row.updated_at = kwargs["updated_at"]
        else:
            # hasattr check: make updated_at present and non-None
            row.updated_at = datetime(2024, 1, 16, 8, 0, 0)
        return row

    def test_happy_path_returns_lead_list(self):
        """get_recent_leads converts DB rows to dict list."""
        row = self._make_row()
        mgr, mock_session = self._make_mgr_with_rows([row])

        leads = mgr.get_recent_leads(limit=10, offset=0)

        assert len(leads) == 1
        lead = leads[0]
        assert lead["email"] == "test@example.com"
        assert lead["name"] == "Test User"
        assert lead["company"] == "ACME"
        assert lead["score"] == pytest.approx(0.85)
        assert lead["tags"] == ["web"]
        assert lead["sourceIds"] == ["web"]
        assert "createdAt" in lead
        mock_session.close.assert_called_once()

    def test_row_with_none_source(self):
        """Rows where source is None → tags=[], sourceIds=[]."""
        row = self._make_row(source=None)
        mgr, _ = self._make_mgr_with_rows([row])

        leads = mgr.get_recent_leads()

        assert leads[0]["tags"] == []
        assert leads[0]["sourceIds"] == []

    def test_row_with_none_extracted_at(self):
        """Rows where extracted_at is None → createdAt is None."""
        row = self._make_row(extracted_at=None)
        mgr, _ = self._make_mgr_with_rows([row])

        leads = mgr.get_recent_leads()

        assert leads[0]["createdAt"] is None

    def test_row_with_none_updated_at(self):
        """Rows where updated_at is None → updatedAt is None."""
        row = self._make_row(updated_at=None)
        mgr, _ = self._make_mgr_with_rows([row])

        leads = mgr.get_recent_leads()

        assert leads[0]["updatedAt"] is None

    def test_multiple_rows_returned(self):
        """get_recent_leads handles multiple rows."""
        rows = [self._make_row(id=i, email=f"u{i}@co.com") for i in range(5)]
        mgr, _ = self._make_mgr_with_rows(rows)

        leads = mgr.get_recent_leads(limit=5)

        assert len(leads) == 5
        emails = [l["email"] for l in leads]
        assert "u0@co.com" in emails

    def test_exception_returns_empty_list(self):
        """get_recent_leads returns [] on DB exception."""
        mgr, _, mock_session_factory = _mock_engine_and_make_manager()
        mock_session = MagicMock()
        mock_session.execute.side_effect = RuntimeError("connection lost")
        mock_session_factory.return_value = mock_session
        mgr.Session = mock_session_factory

        leads = mgr.get_recent_leads()

        assert leads == []
        mock_session.close.assert_called_once()
