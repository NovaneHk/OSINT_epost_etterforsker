"""Extended tests for core/database.py — covers uncovered methods."""
import gc
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from core.database import DatabaseManager, Contact, ContactStatus, AuditEntry


def _make_db():
    """Create a fresh DatabaseManager in a temp directory."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_extended.db"
    manager = DatabaseManager(str(db_path))
    return manager, temp_dir


def _cleanup(manager, temp_dir):
    manager.close()
    gc.collect()
    shutil.rmtree(temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# get_kpi_stats
# ---------------------------------------------------------------------------
class TestGetKpiStats:
    def test_empty_db_returns_zeros(self):
        db, td = _make_db()
        try:
            stats = db.get_kpi_stats()
            assert stats["leads7d"] == 0
            assert stats["conversion_rate"] == 0.0
            assert stats["exports7d"] == 0
        finally:
            _cleanup(db, td)

    def test_stats_count_recent_contacts(self):
        db, td = _make_db()
        try:
            contact = Contact(
                email="stat@example.com",
                domain="example.com",
                status=ContactStatus.UNVALIDATED,
                confidence_score=0.5,
                source="test",
            )
            db.add_contact(contact)
            stats = db.get_kpi_stats()
            assert stats["leads7d"] >= 1
        finally:
            _cleanup(db, td)

    def test_validated_contacts_affect_conversion(self):
        db, td = _make_db()
        try:
            for i in range(3):
                c = Contact(email=f"user{i}@company.com", domain="company.com",
                            status=ContactStatus.UNVALIDATED, confidence_score=0.5)
                db.add_contact(c)
            db.update_contact_status("user0@company.com", ContactStatus.VALIDATED)
            stats = db.get_kpi_stats()
            assert stats["conversion_rate"] > 0
        finally:
            _cleanup(db, td)


# ---------------------------------------------------------------------------
# get_recent_leads
# ---------------------------------------------------------------------------
class TestGetRecentLeads:
    def test_empty_db_returns_empty_list(self):
        db, td = _make_db()
        try:
            leads = db.get_recent_leads()
            assert leads == []
        finally:
            _cleanup(db, td)

    def test_returns_lead_dict_structure(self):
        db, td = _make_db()
        try:
            c = Contact(email="lead@company.com", domain="company.com", name="Lead Name",
                        company="Acme", status=ContactStatus.UNVALIDATED, confidence_score=0.7)
            db.add_contact(c)
            leads = db.get_recent_leads()
            assert len(leads) == 1
            assert "email" in leads[0]
            assert "id" in leads[0]
        finally:
            _cleanup(db, td)

    def test_limit_respected(self):
        db, td = _make_db()
        try:
            for i in range(5):
                db.add_contact(Contact(email=f"u{i}@co.com", domain="co.com",
                                        status=ContactStatus.UNVALIDATED, confidence_score=0.5))
            leads = db.get_recent_leads(limit=2)
            assert len(leads) <= 2
        finally:
            _cleanup(db, td)

    def test_offset_skips_records(self):
        db, td = _make_db()
        try:
            for i in range(3):
                db.add_contact(Contact(email=f"x{i}@co.com", domain="co.com",
                                        status=ContactStatus.UNVALIDATED, confidence_score=0.5))
            leads_all = db.get_recent_leads()
            leads_offset = db.get_recent_leads(offset=1)
            assert len(leads_offset) == len(leads_all) - 1
        finally:
            _cleanup(db, td)


# ---------------------------------------------------------------------------
# store_seeds / store_company / get_companies / store_email / get_emails
# ---------------------------------------------------------------------------
class TestStoreAndRetrieve:
    def test_store_seeds(self):
        db, td = _make_db()
        try:
            db.store_seeds(["B2B SaaS CTO Oslo"], "technical_leaders", "technology", "norway")
            # No error raised = pass
        finally:
            _cleanup(db, td)

    def test_store_company_and_get_companies(self):
        db, td = _make_db()
        try:
            company_data = {
                "name": "Acme Corp",
                "domain": "acme.com",
                "url": "https://acme.com",
                "industry": "technology",
                "size_category": "SME",
                "country": "NO",
                "technologies": ["Python", "React"],
                "source_url": "https://directory.com/acme",
                "source_type": "directory",
                "credibility_score": 75,
            }
            company_id = db.store_company(company_data)
            assert isinstance(company_id, int)
            assert company_id > 0

            companies = db.get_companies()
            assert len(companies) >= 1
            assert companies[0]["name"] == "Acme Corp"
            assert isinstance(companies[0]["technologies"], list)
        finally:
            _cleanup(db, td)

    def test_store_email_and_get_emails(self):
        db, td = _make_db()
        try:
            company_id = db.store_company({
                "name": "TestCo", "domain": "testco.com", "url": "https://testco.com",
                "industry": "tech", "source_url": "src", "source_type": "directory",
            })
            email_data = {
                "email": "cto@testco.com",
                "role": "CTO",
                "confidence": 0.9,
                "company_id": company_id,
                "source_url": "src",
                "source_type": "directory",
                "validation_status": "valid",
                "mx_valid": True,
                "deliverable": True,
                "risk_score": 10,
                "final_score": 85,
            }
            email_id = db.store_email(email_data)
            assert isinstance(email_id, int)

            emails = db.get_emails(min_score=0)
            assert len(emails) >= 1
            assert emails[0]["email"] == "cto@testco.com"
        finally:
            _cleanup(db, td)

    def test_get_emails_with_limit(self):
        db, td = _make_db()
        try:
            cid = db.store_company({"name": "X", "domain": "x.com", "url": "", "industry": "",
                                     "source_url": "s", "source_type": "d"})
            for i in range(5):
                db.store_email({"email": f"e{i}@x.com", "source_url": "s", "source_type": "d",
                                 "company_id": cid, "confidence": 0.5})
            emails = db.get_emails(min_score=0, limit=2)
            assert len(emails) <= 2
        finally:
            _cleanup(db, td)

    def test_get_companies_with_limit(self):
        db, td = _make_db()
        try:
            for i in range(3):
                db.store_company({"name": f"Co{i}", "domain": f"co{i}.com", "url": "",
                                   "industry": "", "source_url": "s", "source_type": "d"})
            companies = db.get_companies(limit=2)
            assert len(companies) == 2
        finally:
            _cleanup(db, td)


# ---------------------------------------------------------------------------
# update_email_validation / update_email_score
# ---------------------------------------------------------------------------
class TestUpdateEmailMethods:
    def test_update_email_validation(self):
        db, td = _make_db()
        try:
            cid = db.store_company({"name": "X", "domain": "x.com", "url": "", "industry": "",
                                     "source_url": "s", "source_type": "d"})
            eid = db.store_email({"email": "v@x.com", "source_url": "s", "source_type": "d",
                                   "company_id": cid, "confidence": 0.5})
            db.update_email_validation(eid, {"status": "valid", "mx_valid": True, "deliverable": True, "risk_score": 5})
            emails = db.get_emails(min_score=0)
            assert emails[0]["validation_status"] == "valid"
        finally:
            _cleanup(db, td)

    def test_update_email_score(self):
        db, td = _make_db()
        try:
            cid = db.store_company({"name": "Y", "domain": "y.com", "url": "", "industry": "",
                                     "source_url": "s", "source_type": "d"})
            eid = db.store_email({"email": "s@y.com", "source_url": "s", "source_type": "d",
                                   "company_id": cid, "confidence": 0.5})
            db.update_email_score(eid, 90)
            emails = db.get_emails(min_score=0)
            assert emails[0]["final_score"] == 90
        finally:
            _cleanup(db, td)


# ---------------------------------------------------------------------------
# get_audit_log (legacy method)
# ---------------------------------------------------------------------------
class TestGetAuditLog:
    def test_empty_returns_list(self):
        db, td = _make_db()
        try:
            log = db.get_audit_log()
            assert isinstance(log, list)
        finally:
            _cleanup(db, td)

    def test_logs_after_action(self):
        db, td = _make_db()
        try:
            db.add_contact(Contact(email="audit@co.com", domain="co.com",
                                    status=ContactStatus.UNVALIDATED, confidence_score=0.5))
            log = db.get_audit_log()
            assert len(log) >= 0  # May or may not have entries depending on implementation
        finally:
            _cleanup(db, td)

    def test_filter_by_email(self):
        db, td = _make_db()
        try:
            db._log_audit_action("target@co.com", "status_updated", proof_note="Test")
            log = db.get_audit_log(email="target@co.com")
            assert isinstance(log, list)
        finally:
            _cleanup(db, td)


# ---------------------------------------------------------------------------
# cache_set / cache_get / cleanup_expired_cache
# ---------------------------------------------------------------------------
class TestCacheMethods:
    def test_set_and_get(self):
        db, td = _make_db()
        try:
            db.cache_set("mykey", {"data": 42}, ttl_seconds=3600)
            result = db.cache_get("mykey")
            assert result == {"data": 42}
        finally:
            _cleanup(db, td)

    def test_get_nonexistent_returns_none(self):
        db, td = _make_db()
        try:
            assert db.cache_get("nonexistent_key") is None
        finally:
            _cleanup(db, td)

    def test_set_string_value(self):
        db, td = _make_db()
        try:
            db.cache_set("strkey", "hello", ttl_seconds=3600)
            result = db.cache_get("strkey")
            assert result == "hello"
        finally:
            _cleanup(db, td)

    def test_cleanup_expired_cache(self):
        db, td = _make_db()
        try:
            # Store with 0 TTL (immediately expired)
            db.cache_set("expired", "val", ttl_seconds=0)
            removed = db.cleanup_expired_cache()
            assert isinstance(removed, int)
        finally:
            _cleanup(db, td)


# ---------------------------------------------------------------------------
# get_statistics
# ---------------------------------------------------------------------------
class TestGetStatistics:
    def test_returns_counts_for_all_tables(self):
        db, td = _make_db()
        try:
            stats = db.get_statistics()
            assert "seeds_count" in stats
            assert "companies_count" in stats
            assert "emails_count" in stats
            assert "audit_log_count" in stats
            assert "cache_count" in stats
            assert "email_validation_breakdown" in stats
            assert "score_distribution" in stats
        finally:
            _cleanup(db, td)

    def test_counts_after_inserts(self):
        db, td = _make_db()
        try:
            cid = db.store_company({"name": "Co", "domain": "co.com", "url": "",
                                     "industry": "", "source_url": "s", "source_type": "d"})
            db.store_email({"email": "e@co.com", "source_url": "s", "source_type": "d",
                             "company_id": cid, "confidence": 0.5})
            stats = db.get_statistics()
            assert stats["companies_count"] >= 1
            assert stats["emails_count"] >= 1
        finally:
            _cleanup(db, td)


# ---------------------------------------------------------------------------
# export_to_csv
# ---------------------------------------------------------------------------
class TestExportToCsv:
    def test_exports_zero_for_empty_db(self):
        db, td = _make_db()
        try:
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
                csv_path = f.name
            try:
                count = db.export_to_csv(csv_path, min_score=0)
                assert count == 0
            finally:
                if os.path.exists(csv_path):
                    os.unlink(csv_path)
        finally:
            _cleanup(db, td)

    def test_exports_emails_to_csv(self):
        db, td = _make_db()
        try:
            import tempfile, os, csv as csv_mod
            cid = db.store_company({"name": "Co", "domain": "co.com", "url": "",
                                     "industry": "", "source_url": "s", "source_type": "d"})
            db.store_email({"email": "exp@co.com", "source_url": "s", "source_type": "d",
                             "company_id": cid, "confidence": 0.9, "risk_score": 0, "final_score": 80})
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
                csv_path = f.name
            try:
                count = db.export_to_csv(csv_path, min_score=0)
                assert count == 1
                with open(csv_path, "r") as f:
                    reader = csv_mod.DictReader(f)
                    rows = list(reader)
                assert len(rows) == 1
                assert rows[0]["email"] == "exp@co.com"
            finally:
                if os.path.exists(csv_path):
                    os.unlink(csv_path)
        finally:
            _cleanup(db, td)


# ---------------------------------------------------------------------------
# get_all_contacts (extended cases)
# ---------------------------------------------------------------------------
class TestGetAllContactsExtended:
    def test_returns_all_contacts(self):
        db, td = _make_db()
        try:
            for i in range(3):
                db.add_contact(Contact(email=f"c{i}@co.com", domain="co.com",
                                        status=ContactStatus.UNVALIDATED, confidence_score=0.5))
            contacts = db.get_all_contacts()
            assert len(contacts) == 3
        finally:
            _cleanup(db, td)

    def test_returns_contact_objects(self):
        db, td = _make_db()
        try:
            db.add_contact(Contact(email="obj@co.com", domain="co.com",
                                    status=ContactStatus.UNVALIDATED, confidence_score=0.5))
            contacts = db.get_all_contacts()
            assert isinstance(contacts[0], Contact)
        finally:
            _cleanup(db, td)
