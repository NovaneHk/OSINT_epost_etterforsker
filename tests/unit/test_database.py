"""
Unit tests for database management
"""

import gc
import pytest
import tempfile
import shutil
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta

from core.database import DatabaseManager, Contact, ContactStatus, AuditEntry


class TestContact:
    """Test Contact dataclass"""

    def test_contact_creation(self):
        contact = Contact(
            email="test@example.com",
            domain="example.com",
            name="Test User",
            role="Developer",
            company="Test Company",
            sector="technology",
            source="test_source",
            confidence_score=0.85,
            persona_match="technical_leaders",
            status=ContactStatus.VALIDATED
        )

        assert contact.email == "test@example.com"
        assert contact.domain == "example.com"
        assert contact.name == "Test User"
        assert contact.role == "Developer"
        assert contact.company == "Test Company"
        assert contact.sector == "technology"
        assert contact.source == "test_source"
        assert contact.confidence_score == 0.85
        assert contact.persona_match == "technical_leaders"
        assert contact.status == ContactStatus.VALIDATED
        assert contact.created_at is not None
        assert contact.updated_at is not None

    def test_contact_defaults(self):
        contact = Contact(
            email="test@example.com",
            domain="example.com"
        )

        assert contact.email == "test@example.com"
        assert contact.domain == "example.com"
        assert contact.name is None
        assert contact.role is None
        assert contact.company is None
        assert contact.sector is None
        assert contact.source is None
        assert contact.confidence_score == 0.0
        assert contact.persona_match is None
        assert contact.status == ContactStatus.UNVALIDATED
        assert contact.created_at is not None
        assert contact.updated_at is not None


class TestContactStatus:
    """Test ContactStatus enum"""

    def test_contact_status_values(self):
        assert ContactStatus.UNVALIDATED.value == "unvalidated"
        assert ContactStatus.VALIDATED.value == "validated"
        assert ContactStatus.BOUNCED.value == "bounced"
        assert ContactStatus.OPTED_OUT.value == "opted_out"
        assert ContactStatus.CONTACTED.value == "contacted"
        assert ContactStatus.RESPONDED.value == "responded"


class TestAuditEntry:
    """Test AuditEntry dataclass"""

    def test_audit_entry_creation(self):
        entry = AuditEntry(
            action="contact_added",
            entity_type="contact",
            entity_id="test@example.com",
            details={"source": "web_scraping"},
            user_id="system"
        )

        assert entry.action == "contact_added"
        assert entry.entity_type == "contact"
        assert entry.entity_id == "test@example.com"
        assert entry.details == {"source": "web_scraping"}
        assert entry.user_id == "system"
        assert entry.timestamp is not None

    def test_audit_entry_defaults(self):
        entry = AuditEntry(
            action="test_action",
            entity_type="test_entity",
            entity_id="test_id"
        )

        assert entry.action == "test_action"
        assert entry.entity_type == "test_entity"
        assert entry.entity_id == "test_id"
        assert entry.details is None
        assert entry.user_id == "system"
        assert entry.timestamp is not None


class TestDatabaseManager:
    """Test DatabaseManager class"""

    @pytest.fixture
    def temp_db_dir(self):
        """Create temporary directory for test database"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        gc.collect()
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def db_manager(self, temp_db_dir):
        """Create DatabaseManager with temporary database"""
        db_path = Path(temp_db_dir) / "test.db"
        manager = DatabaseManager(str(db_path))
        yield manager
        manager.close()

    def test_init_creates_database_file(self, temp_db_dir):
        """Test that database file is created on initialization"""
        db_path = Path(temp_db_dir) / "test.db"
        db_manager = DatabaseManager(str(db_path))
        try:
            assert db_path.exists()
        finally:
            db_manager.close()

        assert db_path.exists()

        # Test that tables are created
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()

            # Check contacts table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contacts'")
            assert cursor.fetchone() is not None

            # Check audit_log table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
            assert cursor.fetchone() is not None

    def test_add_contact(self, db_manager):
        """Test adding a contact to the database"""
        contact = Contact(
            email="test@example.com",
            domain="example.com",
            name="Test User",
            role="Developer",
            company="Test Company",
            sector="technology",
            source="test_source",
            confidence_score=0.85,
            persona_match="technical_leaders",
            status=ContactStatus.VALIDATED
        )

        result = db_manager.add_contact(contact)
        assert result is True

        # Verify contact was added
        retrieved_contact = db_manager.get_contact("test@example.com")
        assert retrieved_contact is not None
        assert retrieved_contact.email == "test@example.com"
        assert retrieved_contact.name == "Test User"
        assert retrieved_contact.role == "Developer"
        assert retrieved_contact.company == "Test Company"
        assert retrieved_contact.sector == "technology"
        assert retrieved_contact.confidence_score == 0.85

    def test_add_duplicate_contact(self, db_manager):
        """Test adding duplicate contact (should update existing)"""
        contact1 = Contact(
            email="test@example.com",
            domain="example.com",
            name="Test User",
            role="Developer"
        )

        contact2 = Contact(
            email="test@example.com",
            domain="example.com",
            name="Test User Updated",
            role="Senior Developer"
        )

        # Add first contact
        result1 = db_manager.add_contact(contact1)
        assert result1 is True

        # Add second contact (same email)
        result2 = db_manager.add_contact(contact2)
        assert result2 is True

        # Verify updated contact
        retrieved_contact = db_manager.get_contact("test@example.com")
        assert retrieved_contact.name == "Test User Updated"
        assert retrieved_contact.role == "Senior Developer"

    def test_get_contact_not_found(self, db_manager):
        """Test getting non-existent contact"""
        contact = db_manager.get_contact("nonexistent@example.com")
        assert contact is None

    def test_update_contact_status(self, db_manager):
        """Test updating contact status"""
        contact = Contact(
            email="test@example.com",
            domain="example.com",
            status=ContactStatus.UNVALIDATED
        )

        db_manager.add_contact(contact)

        # Update status
        result = db_manager.update_contact_status("test@example.com", ContactStatus.VALIDATED)
        assert result is True

        # Verify status was updated
        retrieved_contact = db_manager.get_contact("test@example.com")
        assert retrieved_contact.status == ContactStatus.VALIDATED

        # Test updating non-existent contact
        result = db_manager.update_contact_status("nonexistent@example.com", ContactStatus.VALIDATED)
        assert result is False

    def test_get_contacts_by_status(self, db_manager):
        """Test getting contacts by status"""
        # Add contacts with different statuses
        contact1 = Contact(email="test1@example.com", domain="example.com", status=ContactStatus.VALIDATED)
        contact2 = Contact(email="test2@example.com", domain="example.com", status=ContactStatus.VALIDATED)
        contact3 = Contact(email="test3@example.com", domain="example.com", status=ContactStatus.BOUNCED)

        db_manager.add_contact(contact1)
        db_manager.add_contact(contact2)
        db_manager.add_contact(contact3)

        # Get validated contacts
        validated_contacts = db_manager.get_contacts_by_status(ContactStatus.VALIDATED)
        assert len(validated_contacts) == 2

        # Get bounced contacts
        bounced_contacts = db_manager.get_contacts_by_status(ContactStatus.BOUNCED)
        assert len(bounced_contacts) == 1

        # Get non-existent status
        opted_out_contacts = db_manager.get_contacts_by_status(ContactStatus.OPTED_OUT)
        assert len(opted_out_contacts) == 0

    def test_get_contacts_by_domain(self, db_manager):
        """Test getting contacts by domain"""
        contact1 = Contact(email="test1@example.com", domain="example.com")
        contact2 = Contact(email="test2@example.com", domain="example.com")
        contact3 = Contact(email="test3@different.com", domain="different.com")

        db_manager.add_contact(contact1)
        db_manager.add_contact(contact2)
        db_manager.add_contact(contact3)

        # Get contacts from example.com
        example_contacts = db_manager.get_contacts_by_domain("example.com")
        assert len(example_contacts) == 2

        # Get contacts from different.com
        different_contacts = db_manager.get_contacts_by_domain("different.com")
        assert len(different_contacts) == 1

        # Get contacts from non-existent domain
        nonexistent_contacts = db_manager.get_contacts_by_domain("nonexistent.com")
        assert len(nonexistent_contacts) == 0

    def test_search_contacts(self, db_manager):
        """Test searching contacts"""
        contact1 = Contact(email="john.doe@example.com", domain="example.com", name="John Doe", company="Acme Corp")
        contact2 = Contact(email="jane.smith@example.com", domain="example.com", name="Jane Smith", company="Beta Inc")
        contact3 = Contact(email="bob.jones@different.com", domain="different.com", name="Bob Jones", company="Gamma LLC")

        db_manager.add_contact(contact1)
        db_manager.add_contact(contact2)
        db_manager.add_contact(contact3)

        # Search by name
        john_results = db_manager.search_contacts("John")
        assert len(john_results) == 1
        assert john_results[0].email == "john.doe@example.com"

        # Search by company
        corp_results = db_manager.search_contacts("Corp")
        assert len(corp_results) == 1
        assert corp_results[0].company == "Acme Corp"

        # Search by email
        smith_results = db_manager.search_contacts("smith")
        assert len(smith_results) == 1
        assert smith_results[0].name == "Jane Smith"

        # Search with no results
        xyz_results = db_manager.search_contacts("XYZ")
        assert len(xyz_results) == 0

    def test_get_contact_stats(self, db_manager):
        """Test getting contact statistics"""
        # Add contacts with different statuses
        contact1 = Contact(email="test1@example.com", domain="example.com", status=ContactStatus.VALIDATED)
        contact2 = Contact(email="test2@example.com", domain="example.com", status=ContactStatus.VALIDATED)
        contact3 = Contact(email="test3@example.com", domain="example.com", status=ContactStatus.BOUNCED)
        contact4 = Contact(email="test4@example.com", domain="example.com", status=ContactStatus.UNVALIDATED)

        db_manager.add_contact(contact1)
        db_manager.add_contact(contact2)
        db_manager.add_contact(contact3)
        db_manager.add_contact(contact4)

        stats = db_manager.get_contact_stats()

        assert stats['total'] == 4
        assert stats['validated'] == 2
        assert stats['bounced'] == 1
        assert stats['unvalidated'] == 1
        assert stats['contacted'] == 0
        assert stats['responded'] == 0
        assert stats['opted_out'] == 0

    def test_add_audit_entry(self, db_manager):
        """Test adding audit entry"""
        entry = AuditEntry(
            action="contact_added",
            entity_type="contact",
            entity_id="test@example.com",
            details={"source": "web_scraping"},
            user_id="system"
        )

        result = db_manager.add_audit_entry(entry)
        assert result is True

        # Verify audit entry was added
        entries = db_manager.get_audit_entries(limit=1)
        assert len(entries) == 1
        assert entries[0].action == "contact_added"
        assert entries[0].entity_type == "contact"
        assert entries[0].entity_id == "test@example.com"

    def test_get_audit_entries(self, db_manager):
        """Test getting audit entries"""
        # Add multiple audit entries
        for i in range(5):
            entry = AuditEntry(
                action=f"action_{i}",
                entity_type="contact",
                entity_id=f"test{i}@example.com"
            )
            db_manager.add_audit_entry(entry)

        # Get all entries
        all_entries = db_manager.get_audit_entries()
        assert len(all_entries) == 5

        # Get limited entries
        limited_entries = db_manager.get_audit_entries(limit=3)
        assert len(limited_entries) == 3

        # Entries should be ordered by timestamp (newest first)
        timestamps = [entry.timestamp for entry in limited_entries]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_cleanup_old_data(self, db_manager):
        """Test cleaning up old data"""
        # Add recent contact
        recent_contact = Contact(email="recent@example.com", domain="example.com")
        db_manager.add_contact(recent_contact)

        # Add old contact by manually updating the database
        old_date = datetime.now() - timedelta(days=100)
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO contacts (email, domain, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, ("old@example.com", "example.com", old_date, old_date))
            conn.commit()

        # Add recent and old audit entries
        recent_entry = AuditEntry(action="recent_action", entity_type="contact", entity_id="recent@example.com")
        db_manager.add_audit_entry(recent_entry)

        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_log (action, entity_type, entity_id, timestamp)
                VALUES (?, ?, ?, ?)
            """, ("old_action", "contact", "old@example.com", old_date))
            conn.commit()

        # Cleanup data older than 30 days
        deleted_contacts, deleted_audit_entries = db_manager.cleanup_old_data(days=30)

        assert deleted_contacts == 1
        assert deleted_audit_entries == 1

        # Verify recent data still exists
        recent_contact_check = db_manager.get_contact("recent@example.com")
        assert recent_contact_check is not None

        # Verify old data was deleted
        old_contact_check = db_manager.get_contact("old@example.com")
        assert old_contact_check is None

    def test_close_connection(self, db_manager):
        """Test closing database connection"""
        # Add a contact to ensure connection is working
        contact = Contact(email="test@example.com", domain="example.com")
        result = db_manager.add_contact(contact)
        assert result is True

        # Close connection
        db_manager.close()

        # Try to add another contact (should fail or create new connection)
        contact2 = Contact(email="test2@example.com", domain="example.com")
        # This might fail or succeed depending on implementation
        # The test is mainly to ensure close() doesn't raise an exception