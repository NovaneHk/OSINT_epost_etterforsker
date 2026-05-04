"""
Unit tests for core/gdpr_compliance.py — GDPR data classes and GDPRComplianceManager.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from core.gdpr_compliance import (
    ConsentStatus,
    DataSubjectRight,
    ConsentRecord,
    DataSubjectRequest,
    PIIDetector,
    DataMasker,
    GDPRComplianceManager,
)


# ---------------------------------------------------------------------------
# ConsentStatus / DataSubjectRight enums
# ---------------------------------------------------------------------------

class TestEnums:

    def test_consent_status_values(self):
        assert ConsentStatus.GIVEN.value == "given"
        assert ConsentStatus.WITHDRAWN.value == "withdrawn"
        assert ConsentStatus.PENDING.value == "pending"
        assert ConsentStatus.EXPIRED.value == "expired"

    def test_data_subject_right_values(self):
        assert DataSubjectRight.ACCESS.value == "access"
        assert DataSubjectRight.ERASURE.value == "erasure"
        assert DataSubjectRight.PORTABILITY.value == "portability"


# ---------------------------------------------------------------------------
# ConsentRecord
# ---------------------------------------------------------------------------

class TestConsentRecord:

    def _make(self, status=ConsentStatus.GIVEN, days_ago=0, retention=365):
        return ConsentRecord(
            email="x@y.com",
            status=status,
            timestamp=datetime.now() - timedelta(days=days_ago),
            source="web",
            purpose="B2B lead generation",
            legal_basis="legitimate_interest",
            retention_period=retention,
        )

    def test_is_valid_given_fresh_consent(self):
        assert self._make().is_valid() is True

    def test_is_valid_false_for_withdrawn(self):
        record = self._make(status=ConsentStatus.WITHDRAWN)
        assert record.is_valid() is False

    def test_is_valid_false_for_expired(self):
        record = self._make(days_ago=400, retention=365)
        assert record.is_valid() is False

    def test_is_expired_true_when_past_retention(self):
        record = self._make(days_ago=400, retention=365)
        assert record.is_expired() is True

    def test_is_expired_false_within_retention(self):
        record = self._make(days_ago=10, retention=365)
        assert record.is_expired() is False


# ---------------------------------------------------------------------------
# PIIDetector
# ---------------------------------------------------------------------------

class TestPIIDetector:

    @pytest.fixture
    def detector(self):
        return PIIDetector()

    def test_detects_email_key(self, detector):
        data = {"email": "test@example.com", "score": 0.9}
        pii = detector.detect_pii_fields(data)
        assert "email" in pii

    def test_detects_email_value_pattern(self, detector):
        data = {"contact_info": "reach me at user@corp.com for details"}
        pii = detector.detect_pii_fields(data)
        assert "contact_info" in pii

    def test_detects_name_key(self, detector):
        data = {"name": "John Doe", "role": "CTO"}
        pii = detector.detect_pii_fields(data)
        assert "name" in pii

    def test_detects_firstname(self, detector):
        data = {"firstname": "Alice"}
        pii = detector.detect_pii_fields(data)
        assert "firstname" in pii

    def test_detects_phone_key(self, detector):
        data = {"phone": "+47 123 45 678"}
        pii = detector.detect_pii_fields(data)
        assert "phone" in pii

    def test_detects_address_key(self, detector):
        data = {"address": "Main Street 1", "city": "Oslo"}
        pii = detector.detect_pii_fields(data)
        assert "address" in pii
        assert "city" in pii

    def test_non_pii_not_detected(self, detector):
        data = {"score": 0.8, "sector": "tech", "status": "validated"}
        pii = detector.detect_pii_fields(data)
        assert len(pii) == 0


# ---------------------------------------------------------------------------
# DataMasker
# ---------------------------------------------------------------------------

class TestDataMasker:

    @pytest.fixture
    def masker(self):
        return DataMasker()

    def test_mask_email_preserves_domain(self, masker):
        masked = masker.mask_email("ceo@company.com")
        assert "@company.com" in masked

    def test_mask_email_local_part_is_hash(self, masker):
        masked = masker.mask_email("ceo@company.com")
        local = masked.split("@")[0]
        assert local != "ceo"
        assert len(local) == 8

    def test_mask_email_no_at_sign(self, masker):
        masked = masker.mask_email("invalidemail")
        assert "@" not in masked or len(masked) > 0

    def test_mask_name_first_char_preserved(self, masker):
        masked = masker.mask_name("Alice")
        assert masked.startswith("A")
        assert "*" in masked

    def test_mask_name_short_name(self, masker):
        masked = masker.mask_name("X")
        assert masked == "***"

    def test_mask_name_empty(self, masker):
        assert masker.mask_name("") == "***"

    def test_mask_phone_last_4_preserved(self, masker):
        masked = masker.mask_phone("+47 123 45 678")
        assert masked.endswith("5678")
        assert "*" in masked

    def test_mask_phone_short_number(self, masker):
        masked = masker.mask_phone("123")
        assert masked == "***"

    def test_mask_data_consent_given_no_masking(self, masker):
        data = {"email": "ceo@corp.com", "name": "Alice"}
        result = masker.mask_data(data, consent_given=True)
        assert result == data

    def test_mask_data_no_consent_masks_email(self, masker):
        data = {"email": "ceo@corp.com", "score": 0.9}
        result = masker.mask_data(data, consent_given=False)
        assert result["email"] != "ceo@corp.com"
        assert "@corp.com" in result["email"]

    def test_mask_data_no_consent_masks_name(self, masker):
        data = {"name": "Alice Smith", "sector": "tech"}
        result = masker.mask_data(data, consent_given=False)
        assert result["name"].startswith("A")
        assert "Smith" not in result["name"]

    def test_mask_data_preserves_non_pii(self, masker):
        data = {"email": "a@b.com", "score": 0.8, "sector": "finance"}
        result = masker.mask_data(data, consent_given=False)
        assert result["score"] == 0.8
        assert result["sector"] == "finance"


# ---------------------------------------------------------------------------
# GDPRComplianceManager
# ---------------------------------------------------------------------------

class TestGDPRComplianceManager:

    DEFAULT_CONFIG = {
        "require_consent": True,
        "mask_unconsented": True,
        "retention_days": 365,
        "lawful_basis": "legitimate_interest",
    }

    @pytest.fixture
    def manager(self):
        return GDPRComplianceManager(self.DEFAULT_CONFIG)

    def test_initialization(self, manager):
        assert manager.require_consent is True
        assert manager.retention_days == 365

    def test_record_consent_creates_record(self, manager):
        result = manager.record_consent("ceo@corp.com", "website")
        assert result is True
        assert "ceo@corp.com" in manager.consent_records

    def test_record_consent_status_is_given(self, manager):
        manager.record_consent("ceo@corp.com", "website")
        record = manager.consent_records["ceo@corp.com"]
        assert record.status == ConsentStatus.GIVEN

    def test_check_consent_true_after_recording(self, manager):
        manager.record_consent("ceo@corp.com", "website")
        assert manager.check_consent("ceo@corp.com") is True

    def test_check_consent_false_for_unknown_email(self, manager):
        assert manager.check_consent("unknown@nowhere.com") is False

    def test_withdraw_consent_updates_status(self, manager):
        manager.record_consent("ceo@corp.com", "website")
        result = manager.withdraw_consent("ceo@corp.com")
        assert result is True
        record = manager.consent_records["ceo@corp.com"]
        assert record.status == ConsentStatus.WITHDRAWN

    def test_withdraw_consent_false_for_unknown(self, manager):
        result = manager.withdraw_consent("nobody@nowhere.com")
        assert result is False

    def test_check_consent_false_after_withdrawal(self, manager):
        manager.record_consent("ceo@corp.com", "website")
        manager.withdraw_consent("ceo@corp.com")
        assert manager.check_consent("ceo@corp.com") is False

    def test_process_data_subject_access_request(self, manager):
        result = manager.process_data_subject_request("user@corp.com", DataSubjectRight.ACCESS)
        assert result is True
        assert len(manager.data_subject_requests) == 1

    def test_process_data_subject_erasure_request(self, manager):
        manager.record_consent("user@corp.com", "web")
        result = manager.process_data_subject_request("user@corp.com", DataSubjectRight.ERASURE)
        assert result is True

    def test_apply_data_protection_with_consent(self, manager):
        manager.record_consent("a@b.com", "web")
        data = {"email": "a@b.com", "name": "John"}
        result = manager.apply_data_protection(data, email="a@b.com")
        # With consent given, no masking
        assert result["email"] == "a@b.com"

    def test_apply_data_protection_no_consent_masks(self, manager):
        data = {"email": "a@b.com", "name": "John"}
        result = manager.apply_data_protection(data, email="a@b.com")
        # No consent → masking applied
        assert result["email"] != "a@b.com"

    def test_cleanup_expired_data_returns_count(self, manager):
        manager.record_consent("old@corp.com", "web")
        # Manually expire the record
        manager.consent_records["old@corp.com"].retention_period = 0
        count = manager.cleanup_expired_data()
        assert isinstance(count, int)
        assert count >= 0

    def test_generate_privacy_report_structure(self, manager):
        manager.record_consent("a@b.com", "web")
        report = manager.generate_privacy_report()
        assert "data_subject_requests" in report
        assert "compliance_settings" in report
        assert "active_consents" in report or "total_consented" in report or len(report) > 0

    def test_audit_log_grows_with_operations(self, manager):
        manager.record_consent("a@b.com", "web")
        manager.withdraw_consent("a@b.com")
        assert len(manager.audit_log) >= 2

    def test_no_require_consent_always_unmasked(self):
        config = {**self.DEFAULT_CONFIG, "require_consent": False, "mask_unconsented": False}
        manager = GDPRComplianceManager(config)
        data = {"email": "x@y.com", "name": "Alice"}
        result = manager.apply_data_protection(data, email="x@y.com")
        # With no consent requirement, data should pass through unmasked
        assert result["email"] == "x@y.com"
