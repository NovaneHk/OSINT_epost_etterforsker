"""
GDPR Compliance Module
Handles GDPR compliance requirements including consent management, data masking, and retention policies
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import json
import re

logger = logging.getLogger(__name__)

class ConsentStatus(Enum):
    """Consent status enumeration."""
    GIVEN = "given"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"
    EXPIRED = "expired"

class DataSubjectRight(Enum):
    """Data subject rights under GDPR."""
    ACCESS = "access"
    RECTIFICATION = "rectification"
    ERASURE = "erasure"
    PORTABILITY = "portability"
    RESTRICTION = "restriction"
    OBJECTION = "objection"

@dataclass
class ConsentRecord:
    """Consent record for GDPR compliance."""
    email: str
    status: ConsentStatus
    timestamp: datetime
    source: str
    purpose: str
    legal_basis: str
    retention_period: int  # days

    def is_valid(self) -> bool:
        """Check if consent is still valid."""
        if self.status != ConsentStatus.GIVEN:
            return False

        expiry_date = self.timestamp + timedelta(days=self.retention_period)
        return datetime.now() < expiry_date

    def is_expired(self) -> bool:
        """Check if consent has expired."""
        expiry_date = self.timestamp + timedelta(days=self.retention_period)
        return datetime.now() >= expiry_date

@dataclass
class DataSubjectRequest:
    """Data subject request for GDPR rights."""
    email: str
    request_type: DataSubjectRight
    timestamp: datetime
    status: str
    notes: Optional[str] = None

class PIIDetector:
    """Detects and classifies personally identifiable information."""

    def __init__(self):
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.phone_pattern = re.compile(r'(\+\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}')
        self.name_indicators = ['name', 'firstname', 'lastname', 'fullname', 'contact']

    def detect_pii_fields(self, data: Dict[str, Any]) -> Set[str]:
        """Detect PII fields in data dictionary."""
        pii_fields = set()

        for key, value in data.items():
            key_lower = key.lower()

            # Check for email fields
            if 'email' in key_lower or (isinstance(value, str) and self.email_pattern.search(value)):
                pii_fields.add(key)

            # Check for name fields
            elif any(indicator in key_lower for indicator in self.name_indicators):
                pii_fields.add(key)

            # Check for phone fields
            elif 'phone' in key_lower or 'tel' in key_lower or (isinstance(value, str) and self.phone_pattern.search(value)):
                pii_fields.add(key)

            # Check for address fields
            elif any(addr in key_lower for addr in ['address', 'street', 'city', 'postal', 'zip']):
                pii_fields.add(key)

        return pii_fields

class DataMasker:
    """Masks PII data for GDPR compliance."""

    def __init__(self):
        self.pii_detector = PIIDetector()

    def mask_email(self, email: str) -> str:
        """Mask email address while preserving domain for analytics."""
        if '@' not in email:
            return self._hash_string(email)

        local, domain = email.split('@', 1)
        masked_local = self._hash_string(local)[:8]
        return f"{masked_local}@{domain}"

    def mask_name(self, name: str) -> str:
        """Mask personal name."""
        if not name or len(name) < 2:
            return "***"

        return name[0] + "*" * (len(name) - 1)

    def mask_phone(self, phone: str) -> str:
        """Mask phone number."""
        digits_only = re.sub(r'\D', '', phone)
        if len(digits_only) < 4:
            return "***"

        return "*" * (len(digits_only) - 4) + digits_only[-4:]

    def mask_data(self, data: Dict[str, Any], consent_given: bool = False) -> Dict[str, Any]:
        """Mask PII data based on consent status."""
        if consent_given:
            return data

        masked_data = data.copy()
        pii_fields = self.pii_detector.detect_pii_fields(data)

        for field in pii_fields:
            if field in masked_data:
                value = masked_data[field]
                if isinstance(value, str):
                    if 'email' in field.lower():
                        masked_data[field] = self.mask_email(value)
                    elif any(name_ind in field.lower() for name_ind in ['name', 'contact']):
                        masked_data[field] = self.mask_name(value)
                    elif any(phone_ind in field.lower() for phone_ind in ['phone', 'tel']):
                        masked_data[field] = self.mask_phone(value)
                    else:
                        masked_data[field] = self._hash_string(value)[:8] + "***"

        return masked_data

    def _hash_string(self, value: str) -> str:
        """Hash string for anonymization."""
        return hashlib.sha256(value.encode()).hexdigest()

class GDPRComplianceManager:
    """Manages GDPR compliance for the OSINT system."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.consent_records: Dict[str, ConsentRecord] = {}
        self.data_subject_requests: List[DataSubjectRequest] = []
        self.data_masker = DataMasker()
        self.audit_log: List[Dict[str, Any]] = []

        # Load configuration
        self.require_consent = config.get('require_consent', True)
        self.mask_unconsented = config.get('mask_unconsented', True)
        self.retention_days = config.get('retention_days', 365)
        self.lawful_basis = config.get('lawful_basis', 'legitimate_interest')

    def record_consent(self, email: str, source: str, purpose: str = "B2B lead generation") -> bool:
        """Record consent for data processing."""
        try:
            consent = ConsentRecord(
                email=email,
                status=ConsentStatus.GIVEN,
                timestamp=datetime.now(),
                source=source,
                purpose=purpose,
                legal_basis=self.lawful_basis,
                retention_period=self.retention_days
            )

            self.consent_records[email] = consent
            self._audit_log("consent_recorded", {"email": email, "source": source})

            logger.info(f"Consent recorded for {email} from {source}")
            return True

        except Exception as e:
            logger.error(f"Failed to record consent for {email}: {e}")
            return False

    def withdraw_consent(self, email: str, reason: str = "User request") -> bool:
        """Withdraw consent for data processing."""
        try:
            if email in self.consent_records:
                self.consent_records[email].status = ConsentStatus.WITHDRAWN
                self._audit_log("consent_withdrawn", {"email": email, "reason": reason})

                logger.info(f"Consent withdrawn for {email}: {reason}")
                return True
            else:
                logger.warning(f"No consent record found for {email}")
                return False

        except Exception as e:
            logger.error(f"Failed to withdraw consent for {email}: {e}")
            return False

    def check_consent(self, email: str) -> bool:
        """Check if valid consent exists for email processing."""
        if not self.require_consent:
            return True

        if email not in self.consent_records:
            return False

        consent = self.consent_records[email]

        # Check if consent is expired
        if consent.is_expired():
            consent.status = ConsentStatus.EXPIRED
            self._audit_log("consent_expired", {"email": email})
            return False

        return consent.is_valid()

    def process_data_subject_request(self, email: str, request_type: DataSubjectRight, notes: str = None) -> bool:
        """Process data subject rights request."""
        try:
            request = DataSubjectRequest(
                email=email,
                request_type=request_type,
                timestamp=datetime.now(),
                status="received",
                notes=notes
            )

            self.data_subject_requests.append(request)
            self._audit_log("data_subject_request", {
                "email": email,
                "request_type": request_type.value,
                "notes": notes
            })

            # Handle specific request types
            if request_type == DataSubjectRight.ERASURE:
                self._handle_erasure_request(email)
            elif request_type == DataSubjectRight.OBJECTION:
                self.withdraw_consent(email, "Data subject objection")

            logger.info(f"Data subject request processed: {request_type.value} for {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to process data subject request for {email}: {e}")
            return False

    def _handle_erasure_request(self, email: str) -> None:
        """Handle right to erasure (right to be forgotten)."""
        # Remove consent record
        if email in self.consent_records:
            del self.consent_records[email]

        # Mark for deletion in database (implementation depends on database layer)
        self._audit_log("erasure_processed", {"email": email})

    def apply_data_protection(self, data: Dict[str, Any], email: str = None) -> Dict[str, Any]:
        """Apply data protection measures based on consent status."""
        if not email:
            # Try to extract email from data
            email = self._extract_email_from_data(data)

        if not email:
            # If no email found and masking required, mask all PII
            if self.mask_unconsented:
                return self.data_masker.mask_data(data, consent_given=False)
            return data

        consent_given = self.check_consent(email)

        if self.mask_unconsented and not consent_given:
            return self.data_masker.mask_data(data, consent_given=False)

        return data

    def _extract_email_from_data(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract email from data dictionary."""
        for key, value in data.items():
            if 'email' in key.lower() and isinstance(value, str) and '@' in value:
                return value
        return None

    def cleanup_expired_data(self) -> int:
        """Clean up expired consent records and data."""
        expired_count = 0
        expired_emails = []

        for email, consent in self.consent_records.items():
            if consent.is_expired():
                expired_emails.append(email)
                expired_count += 1

        # Remove expired consent records
        for email in expired_emails:
            del self.consent_records[email]
            self._audit_log("expired_data_cleaned", {"email": email})

        logger.info(f"Cleaned up {expired_count} expired consent records")
        return expired_count

    def generate_privacy_report(self) -> Dict[str, Any]:
        """Generate privacy compliance report."""
        total_consents = len(self.consent_records)
        valid_consents = sum(1 for consent in self.consent_records.values() if consent.is_valid())
        expired_consents = sum(1 for consent in self.consent_records.values() if consent.is_expired())

        return {
            'timestamp': datetime.now().isoformat(),
            'total_consent_records': total_consents,
            'valid_consents': valid_consents,
            'expired_consents': expired_consents,
            'data_subject_requests': len(self.data_subject_requests),
            'audit_log_entries': len(self.audit_log),
            'compliance_settings': {
                'require_consent': self.require_consent,
                'mask_unconsented': self.mask_unconsented,
                'retention_days': self.retention_days,
                'lawful_basis': self.lawful_basis
            }
        }

    def _audit_log(self, action: str, details: Dict[str, Any]) -> None:
        """Add entry to audit log."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'details': details
        }
        self.audit_log.append(log_entry)

        # Keep audit log size manageable
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-5000:]  # Keep last 5000 entries

    def export_audit_log(self, start_date: datetime = None, end_date: datetime = None) -> List[Dict[str, Any]]:
        """Export audit log for compliance reporting."""
        if not start_date and not end_date:
            return self.audit_log

        filtered_log = []
        for entry in self.audit_log:
            entry_date = datetime.fromisoformat(entry['timestamp'])

            if start_date and entry_date < start_date:
                continue
            if end_date and entry_date > end_date:
                continue

            filtered_log.append(entry)

        return filtered_log

    def validate_compliance(self) -> Dict[str, Any]:
        """Validate GDPR compliance status."""
        issues = []
        warnings = []

        # Check consent management
        if self.require_consent and not self.consent_records:
            warnings.append("No consent records found - ensure consent is being collected")

        # Check data masking
        if not self.mask_unconsented:
            warnings.append("Data masking disabled - PII may be exposed without consent")

        # Check retention period
        if self.retention_days > 1095:  # 3 years
            warnings.append("Long retention period - consider reducing for better compliance")

        # Check audit logging
        if not self.audit_log:
            issues.append("No audit log entries - audit logging may not be working")

        return {
            'compliant': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'recommendations': [
                "Regularly review and clean up expired data",
                "Implement automated consent renewal processes",
                "Provide clear privacy notices to data subjects",
                "Train staff on GDPR compliance procedures"
            ]
        }
