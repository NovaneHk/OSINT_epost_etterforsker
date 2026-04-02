"""
GDPR Compliance Module
Handles data export, erasure, and consent logging per GDPR Article 17/20.
"""

import hashlib
import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

DB_PATH = "data/osint_cache.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class GDPRManager:
    """GDPR right-to-erasure and right-to-portability operations."""

    # ------------------------------------------------------------------
    # Export (Article 20 — data portability)
    # ------------------------------------------------------------------

    def export_lead_data(self, email: str, db: Any = None) -> Dict[str, Any]:
        """Return all stored data for the given email address."""
        conn = _get_conn()
        result: Dict[str, Any] = {"email": email, "leads": [], "contacts": [], "investigations": [], "audit_logs": []}
        try:
            cur = conn.cursor()

            cur.execute("SELECT * FROM leads WHERE email = ?", (email,))
            rows = cur.fetchall()
            result["leads"] = [dict(r) for r in rows]

            cur.execute("SELECT * FROM contacts WHERE email = ?", (email,))
            rows = cur.fetchall()
            result["contacts"] = [dict(r) for r in rows]

            cur.execute(
                "SELECT * FROM investigations WHERE target_email = ?", (email,)
            )
            rows = cur.fetchall()
            result["investigations"] = [dict(r) for r in rows]

            cur.execute(
                "SELECT * FROM audit_log WHERE details LIKE ?", (f"%{email}%",)
            )
            rows = cur.fetchall()
            result["audit_logs"] = [dict(r) for r in rows]

        except sqlite3.OperationalError as exc:
            logger.warning("GDPR export query error: %s", exc)
        finally:
            conn.close()
        return result

    # ------------------------------------------------------------------
    # Erasure (Article 17 — right to be forgotten)
    # ------------------------------------------------------------------

    def erase_lead_data(self, email: str, db: Any = None) -> int:
        """
        Anonymise leads/contacts and delete investigation rows.
        Returns count of affected rows.
        """
        anon_email = "gdpr-erased-" + hashlib.sha256(email.encode()).hexdigest()[:12] + "@erased.invalid"
        affected = 0
        conn = _get_conn()
        try:
            cur = conn.cursor()

            cur.execute(
                """UPDATE leads
                   SET name = 'SLETTET', email = ?, phone = NULL,
                       company = NULL, job_title = NULL, linkedin_url = NULL,
                       twitter_handle = NULL, website = NULL
                   WHERE email = ?""",
                (anon_email, email),
            )
            affected += cur.rowcount

            cur.execute(
                """UPDATE contacts
                   SET name = 'SLETTET', email = ?, phone = NULL
                   WHERE email = ?""",
                (anon_email, email),
            )
            affected += cur.rowcount

            cur.execute(
                "DELETE FROM investigations WHERE target_email = ?", (email,)
            )
            affected += cur.rowcount

            conn.commit()
        except sqlite3.OperationalError as exc:
            logger.warning("GDPR erase query error: %s", exc)
            conn.rollback()
        finally:
            conn.close()
        return affected

    # ------------------------------------------------------------------
    # Consent logging
    # ------------------------------------------------------------------

    def log_request(self, action: str, email: str, requested_by: str, db: Any = None) -> None:
        """Write a GDPR action to audit_log."""
        conn = _get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO audit_log (user_id, action, resource_path, details, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    requested_by,
                    f"GDPR_{action.upper()}",
                    f"/api/gdpr/{action}/{email}",
                    f"GDPR {action} requested for {email}",
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
        except sqlite3.OperationalError as exc:
            logger.warning("GDPR audit log error: %s", exc)
        finally:
            conn.close()


gdpr_manager = GDPRManager()
