"""
Extended unit tests for core/gdpr_compliance.py
Targets uncovered lines: 145-148, 191-193, 208-226, 252, 257-259,
                          274, 278-280, 291-294, 346, 350-364, 368-387
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from core.gdpr_compliance import (
    ConsentRecord,
    ConsentStatus,
    DataSubjectRequest,
    DataSubjectRight,
    DataMasker,
    GDPRComplianceManager,
    PIIDetector,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager(**kwargs):
    cfg = {
        "require_consent": True,
        "mask_unconsented": True,
        "retention_days": 365,
        "lawful_basis": "legitimate_interest",
        **kwargs,
    }
    return GDPRComplianceManager(cfg)


def _fresh_consent(email="test@example.com"):
    return ConsentRecord(
        email=email,
        status=ConsentStatus.GIVEN,
        timestamp=datetime.now(),
        source="web",
        purpose="B2B lead generation",
        legal_basis="legitimate_interest",
        retention_period=365,
    )


# ---------------------------------------------------------------------------
# DataMasker — phone and generic hash branches (lines 145-148, 191-193)
# ---------------------------------------------------------------------------

class TestDataMaskerPhoneBranch:

    def test_mask_data_phone_field_masked(self):
        """Phone fields should be masked via mask_phone (lines 145-148)."""
        masker = DataMasker()
        data = {"phone": "12345678"}
        result = masker.mask_data(data, consent_given=False)
        # Last 4 digits of "12345678" → "5678", rest masked
        assert result["phone"].endswith("5678")
        assert result["phone"] != "12345678"

    def test_mask_data_tel_field_masked(self):
        """Tel fields also trigger phone masking."""
        masker = DataMasker()
        data = {"tel": "47123456"}
        result = masker.mask_data(data, consent_given=False)
        assert result["tel"].endswith("3456")

    def test_mask_data_generic_pii_field_hash(self):
        """PII fields that are not email/name/phone get a hash (lines 191-193)."""
        masker = DataMasker()
        # 'address' is a PII field but not email/name/phone → generic hash branch
        data = {"address": "123 Main Street"}
        result = masker.mask_data(data, consent_given=False)
        assert result["address"] != "123 Main Street"
        assert result["address"].endswith("***")

    def test_mask_data_street_field_hash(self):
        masker = DataMasker()
        data = {"street": "Baker Street 221B"}
        result = masker.mask_data(data, consent_given=False)
        assert result["street"].endswith("***")

    def test_mask_data_non_string_pii_not_touched(self):
        """Non-string PII values should remain unchanged (isinstance guard)."""
        masker = DataMasker()
        data = {"phone": 12345678}  # integer, not string
        result = masker.mask_data(data, consent_given=False)
        # The value is not a string, so masking is skipped
        assert result["phone"] == 12345678


# ---------------------------------------------------------------------------
# GDPRComplianceManager — apply_data_protection edge cases (lines 208-226)
# ---------------------------------------------------------------------------

class TestApplyDataProtection:

    def test_no_email_param_extracted_from_data(self):
        """When email= is None but data contains email key, it is extracted."""
        mgr = _make_manager()
        mgr.record_consent("user@corp.com", "web")
        data = {"email": "user@corp.com", "name": "John"}
        result = mgr.apply_data_protection(data)
        # Consent was given → data returned unchanged
        assert result["email"] == "user@corp.com"

    def test_no_email_anywhere_mask_unconsented_true(self):
        """No email in call or data → masks all PII when mask_unconsented=True."""
        mgr = _make_manager(mask_unconsented=True)
        data = {"name": "Jane Doe", "score": 42}
        result = mgr.apply_data_protection(data, email=None)
        assert result["name"] != "Jane Doe"

    def test_no_email_anywhere_mask_unconsented_false(self):
        """No email in call or data → returns data unchanged when mask_unconsented=False."""
        mgr = _make_manager(mask_unconsented=False)
        data = {"name": "Jane Doe", "score": 42}
        result = mgr.apply_data_protection(data, email=None)
        assert result["name"] == "Jane Doe"

    def test_explicit_email_with_consent_returns_raw_data(self):
        """Explicit email with valid consent → raw data returned (lines 291-294)."""
        mgr = _make_manager()
        mgr.record_consent("a@b.com", "api")
        data = {"email": "a@b.com", "revenue": 5000}
        result = mgr.apply_data_protection(data, email="a@b.com")
        assert result["email"] == "a@b.com"

    def test_explicit_email_no_consent_masks_when_configured(self):
        """Explicit email without consent masks PII when mask_unconsented=True."""
        mgr = _make_manager()
        data = {"email": "no@consent.com", "name": "Alice"}
        result = mgr.apply_data_protection(data, email="no@consent.com")
        assert result["email"] != "no@consent.com"

    def test_expired_consent_triggers_masking(self):
        """Expired consent → check_consent returns False → data is masked."""
        mgr = _make_manager()
        old_consent = ConsentRecord(
            email="old@user.com",
            status=ConsentStatus.GIVEN,
            timestamp=datetime.now() - timedelta(days=400),
            source="web",
            purpose="B2B",
            legal_basis="legitimate_interest",
            retention_period=365,
        )
        mgr.consent_records["old@user.com"] = old_consent
        data = {"email": "old@user.com", "name": "Old User"}
        result = mgr.apply_data_protection(data, email="old@user.com")
        assert result["email"] != "old@user.com"


# ---------------------------------------------------------------------------
# GDPRComplianceManager — process_data_subject_request OBJECTION (line 252)
# ---------------------------------------------------------------------------

class TestProcessDataSubjectRequestObjection:

    def test_objection_withdraws_consent(self):
        """OBJECTION request should withdraw consent (line 252)."""
        mgr = _make_manager()
        mgr.record_consent("obj@user.com", "web")
        assert mgr.check_consent("obj@user.com") is True

        mgr.process_data_subject_request("obj@user.com", DataSubjectRight.OBJECTION)

        assert mgr.check_consent("obj@user.com") is False

    def test_objection_adds_to_requests_list(self):
        mgr = _make_manager()
        mgr.process_data_subject_request("obj2@user.com", DataSubjectRight.OBJECTION)
        assert any(r.request_type == DataSubjectRight.OBJECTION for r in mgr.data_subject_requests)

    def test_process_request_exception_returns_false(self):
        """Exception during processing → returns False (lines 257-259)."""
        mgr = _make_manager()
        with patch.object(mgr, "_audit_log", side_effect=Exception("audit crash")):
            result = mgr.process_data_subject_request("x@y.com", DataSubjectRight.ACCESS)
        assert result is False


# ---------------------------------------------------------------------------
# GDPRComplianceManager — _handle_erasure_request audit (lines 274, 278-280)
# ---------------------------------------------------------------------------

class TestHandleErasureRequest:

    def test_erasure_removes_consent_record(self):
        mgr = _make_manager()
        mgr.record_consent("del@user.com", "web")
        assert "del@user.com" in mgr.consent_records

        mgr._handle_erasure_request("del@user.com")

        assert "del@user.com" not in mgr.consent_records

    def test_erasure_adds_audit_entry(self):
        mgr = _make_manager()
        mgr.record_consent("del2@user.com", "web")
        initial_log_size = len(mgr.audit_log)

        mgr._handle_erasure_request("del2@user.com")

        assert len(mgr.audit_log) > initial_log_size
        assert any(e["action"] == "erasure_processed" for e in mgr.audit_log)

    def test_erasure_no_consent_record_still_logs(self):
        """Erasure with no consent record should still log (lines 278-280)."""
        mgr = _make_manager()
        # No consent record for this email
        mgr._handle_erasure_request("nobody@user.com")
        assert any(e["action"] == "erasure_processed" for e in mgr.audit_log)

    def test_erasure_via_process_request(self):
        """ERASURE data subject request triggers _handle_erasure_request."""
        mgr = _make_manager()
        mgr.record_consent("erase@user.com", "web")
        mgr.process_data_subject_request("erase@user.com", DataSubjectRight.ERASURE)
        assert "erase@user.com" not in mgr.consent_records


# ---------------------------------------------------------------------------
# GDPRComplianceManager — audit log trim (line 346)
# ---------------------------------------------------------------------------

class TestAuditLogTrim:

    def test_audit_log_trimmed_at_10000(self):
        """Audit log is trimmed to last 5000 when it exceeds 10000 (line 346)."""
        mgr = _make_manager()
        # Fill the audit log with 10000 entries
        mgr.audit_log = [
            {"timestamp": datetime.now().isoformat(), "action": f"ev{i}", "details": {}}
            for i in range(10001)
        ]
        # Trigger the trim by adding one more entry
        mgr._audit_log("trigger", {})
        assert len(mgr.audit_log) == 5000


# ---------------------------------------------------------------------------
# GDPRComplianceManager — export_audit_log with date filters (lines 350-364)
# ---------------------------------------------------------------------------

class TestExportAuditLog:

    def _make_mgr_with_log(self):
        mgr = _make_manager()
        # Create entries spread over three days
        for days_ago in [3, 2, 1, 0]:
            ts = (datetime.now() - timedelta(days=days_ago)).isoformat()
            mgr.audit_log.append({"timestamp": ts, "action": "ev", "details": {}})
        return mgr

    def test_no_filter_returns_all(self):
        mgr = self._make_mgr_with_log()
        result = mgr.export_audit_log()
        assert len(result) == 4

    def test_start_date_filter(self):
        mgr = self._make_mgr_with_log()
        start = datetime.now() - timedelta(days=1, hours=12)
        result = mgr.export_audit_log(start_date=start)
        # Only today and yesterday entries pass
        assert len(result) == 2

    def test_end_date_filter(self):
        mgr = self._make_mgr_with_log()
        end = datetime.now() - timedelta(days=1, hours=12)
        result = mgr.export_audit_log(end_date=end)
        # Only entries 3 and 2 days ago pass
        assert len(result) == 2

    def test_start_and_end_date_filter(self):
        mgr = self._make_mgr_with_log()
        start = datetime.now() - timedelta(days=2, hours=12)
        end = datetime.now() - timedelta(hours=12)
        result = mgr.export_audit_log(start_date=start, end_date=end)
        # Only 2-days-ago and 1-day-ago entries
        assert len(result) == 2

    def test_empty_log_returns_empty(self):
        mgr = _make_manager()
        result = mgr.export_audit_log(
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
        )
        assert result == []


# ---------------------------------------------------------------------------
# GDPRComplianceManager — validate_compliance (lines 368-387)
# ---------------------------------------------------------------------------

class TestValidateCompliance:

    def test_no_audit_log_adds_issue(self):
        """Empty audit log → issues list should contain entry."""
        mgr = _make_manager()
        result = mgr.validate_compliance()
        assert not result["compliant"]
        assert any("audit log" in i.lower() for i in result["issues"])

    def test_no_consent_records_adds_warning(self):
        """When require_consent=True and no records → warning added."""
        mgr = _make_manager()
        mgr._audit_log("seed", {})  # prevent audit issue
        result = mgr.validate_compliance()
        assert any("consent" in w.lower() for w in result["warnings"])

    def test_mask_unconsented_false_adds_warning(self):
        """When mask_unconsented=False → warning about PII exposure."""
        mgr = _make_manager(mask_unconsented=False)
        mgr._audit_log("seed", {})
        result = mgr.validate_compliance()
        assert any("masking" in w.lower() for w in result["warnings"])

    def test_long_retention_adds_warning(self):
        """When retention_days > 1095 → warning added."""
        mgr = _make_manager(retention_days=1100)
        mgr._audit_log("seed", {})
        result = mgr.validate_compliance()
        assert any("retention" in w.lower() for w in result["warnings"])

    def test_compliant_when_audit_has_entries_and_consent_recorded(self):
        """When all checks pass → compliant=True with no issues."""
        mgr = _make_manager()
        mgr.record_consent("ok@user.com", "web")
        result = mgr.validate_compliance()
        assert result["compliant"] is True
        assert result["issues"] == []

    def test_returns_all_required_keys(self):
        mgr = _make_manager()
        mgr.record_consent("k@user.com", "web")
        result = mgr.validate_compliance()
        assert "compliant" in result
        assert "issues" in result
        assert "warnings" in result

    def test_require_consent_false_no_consent_warning(self):
        """When require_consent=False, no consent-records warning is raised."""
        mgr = _make_manager(require_consent=False)
        mgr._audit_log("seed", {})
        result = mgr.validate_compliance()
        consent_warnings = [w for w in result["warnings"] if "consent records" in w.lower()]
        assert consent_warnings == []


# ---------------------------------------------------------------------------
# GDPRComplianceManager — check_consent expired path (lines 224-226)
# ---------------------------------------------------------------------------

class TestCheckConsentExpiredPath:

    def test_check_consent_marks_expired_and_returns_false(self):
        """When consent has expired, status is set to EXPIRED and False returned."""
        mgr = _make_manager()
        expired = ConsentRecord(
            email="exp@user.com",
            status=ConsentStatus.GIVEN,
            timestamp=datetime.now() - timedelta(days=400),
            source="web",
            purpose="B2B",
            legal_basis="legitimate_interest",
            retention_period=365,
        )
        mgr.consent_records["exp@user.com"] = expired

        result = mgr.check_consent("exp@user.com")

        assert result is False
        assert mgr.consent_records["exp@user.com"].status == ConsentStatus.EXPIRED

    def test_check_consent_adds_audit_entry_on_expiry(self):
        """Expiry path should add a consent_expired audit entry."""
        mgr = _make_manager()
        mgr.consent_records["exp2@user.com"] = ConsentRecord(
            email="exp2@user.com",
            status=ConsentStatus.GIVEN,
            timestamp=datetime.now() - timedelta(days=400),
            source="web",
            purpose="B2B",
            legal_basis="legitimate_interest",
            retention_period=365,
        )
        mgr.check_consent("exp2@user.com")
        assert any(e["action"] == "consent_expired" for e in mgr.audit_log)


# ---------------------------------------------------------------------------
# GDPRComplianceManager — record_consent exception path
# ---------------------------------------------------------------------------

class TestRecordConsentException:

    def test_record_consent_exception_returns_false(self):
        """When ConsentRecord creation throws, returns False gracefully."""
        mgr = _make_manager()
        with patch("core.gdpr_compliance.ConsentRecord", side_effect=Exception("ctor fail")):
            result = mgr.record_consent("bad@user.com", "web")
        assert result is False


# ---------------------------------------------------------------------------
# GDPRComplianceManager — withdraw_consent exception path
# ---------------------------------------------------------------------------

class TestWithdrawConsentException:

    def test_withdraw_consent_exception_returns_false(self):
        """When withdraw raises, returns False gracefully."""
        mgr = _make_manager()
        mgr.record_consent("ex@user.com", "web")
        with patch.object(mgr, "_audit_log", side_effect=Exception("log fail")):
            result = mgr.withdraw_consent("ex@user.com")
        assert result is False


# ---------------------------------------------------------------------------
# GDPRComplianceManager — cleanup_expired_data
# ---------------------------------------------------------------------------

class TestCleanupExpiredData:

    def test_cleans_up_expired_and_returns_count(self):
        mgr = _make_manager()
        mgr.consent_records["alive@user.com"] = _fresh_consent("alive@user.com")
        mgr.consent_records["dead@user.com"] = ConsentRecord(
            email="dead@user.com",
            status=ConsentStatus.GIVEN,
            timestamp=datetime.now() - timedelta(days=400),
            source="web",
            purpose="B2B",
            legal_basis="legitimate_interest",
            retention_period=365,
        )

        count = mgr.cleanup_expired_data()

        assert count == 1
        assert "dead@user.com" not in mgr.consent_records
        assert "alive@user.com" in mgr.consent_records

    def test_no_expired_returns_zero(self):
        mgr = _make_manager()
        mgr.consent_records["alive@user.com"] = _fresh_consent("alive@user.com")
        assert mgr.cleanup_expired_data() == 0

    def test_audit_logged_per_deletion(self):
        mgr = _make_manager()
        mgr.consent_records["done@user.com"] = ConsentRecord(
            email="done@user.com",
            status=ConsentStatus.GIVEN,
            timestamp=datetime.now() - timedelta(days=400),
            source="web",
            purpose="B2B",
            legal_basis="legitimate_interest",
            retention_period=365,
        )
        mgr.cleanup_expired_data()
        assert any(e["action"] == "expired_data_cleaned" for e in mgr.audit_log)


# ---------------------------------------------------------------------------
# PIIDetector — phone value detection
# ---------------------------------------------------------------------------

class TestPIIDetectorPhoneValue:

    def test_detects_phone_value_pattern(self):
        """Phone number value triggers PII detection even without key hint."""
        detector = PIIDetector()
        data = {"info": "+47 123 45 678"}
        pii = detector.detect_pii_fields(data)
        assert "info" in pii

    def test_detects_zip_address_key(self):
        detector = PIIDetector()
        data = {"zip": "0150", "city": "Oslo", "postal": "0150"}
        pii = detector.detect_pii_fields(data)
        assert "zip" in pii
        assert "city" in pii
        assert "postal" in pii
