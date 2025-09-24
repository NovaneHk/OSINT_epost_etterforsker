"""
Database Management System
Handles SQLite database operations for caching and storage
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class ContactStatus(Enum):
    """Enumeration of contact statuses"""
    UNVALIDATED = "unvalidated"
    VALIDATED = "validated"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    BOUNCED = "bounced"
    INVALID = "invalid"
    BLOCKED = "blocked"


@dataclass
class Contact:
    """Contact data model"""
    email: str
    domain: str
    name: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None
    status: ContactStatus = ContactStatus.UNVALIDATED
    confidence_score: float = 0.0
    overall_score: float = 0.0
    persona_match: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    extracted_at: Optional[datetime] = None
    validated_at: Optional[datetime] = None

    def __post_init__(self):
        """Post-initialization processing"""
        if isinstance(self.status, str):
            self.status = ContactStatus(self.status)
        if self.extracted_at is None:
            self.extracted_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert contact to dictionary"""
        return {
            'email': self.email,
            'domain': self.domain,
            'name': self.name,
            'role': self.role,
            'company': self.company,
            'status': self.status.value if isinstance(self.status, ContactStatus) else self.status,
            'confidence_score': self.confidence_score,
            'overall_score': self.overall_score,
            'persona_match': self.persona_match,
            'source': self.source,
            'source_url': self.source_url,
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None,
            'validated_at': self.validated_at.isoformat() if self.validated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Contact':
        """Create contact from dictionary"""
        contact = cls(
            email=data['email'],
            domain=data['domain'],
            name=data.get('name'),
            role=data.get('role'),
            company=data.get('company'),
            status=ContactStatus(data.get('status', 'unvalidated')),
            confidence_score=data.get('confidence_score', 0.0),
            overall_score=data.get('overall_score', 0.0),
            persona_match=data.get('persona_match'),
            source=data.get('source'),
            source_url=data.get('source_url')
        )

        # Parse datetime fields
        if data.get('extracted_at'):
            contact.extracted_at = datetime.fromisoformat(data['extracted_at'])
        if data.get('validated_at'):
            contact.validated_at = datetime.fromisoformat(data['validated_at'])

        return contact

class DatabaseManager:
    """Manages SQLite database operations for the OSINT system."""

    def __init__(self, db_path: str = "data/osint_cache.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def init_db(self):
        """Public method to initialize database (for testing compatibility)"""
        self._init_database()

    def _init_database(self):
        """Initialize database with required tables."""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Seeds table for search queries
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS seeds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    persona TEXT NOT NULL,
                    sector TEXT NOT NULL,
                    geography TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE
                )
            ''')

            # Companies table for scraped company data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    url TEXT,
                    industry TEXT,
                    size_category TEXT,
                    country TEXT,
                    technologies TEXT, -- JSON array
                    source_url TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    credibility_score INTEGER DEFAULT 50,
                    retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(domain, source_url)
                )
            ''')

            # Emails table for extracted email addresses
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    role TEXT,
                    confidence REAL DEFAULT 0.0,
                    context TEXT,
                    company_id INTEGER,
                    source_url TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    validation_status TEXT DEFAULT 'pending',
                    mx_valid BOOLEAN,
                    deliverable BOOLEAN,
                    risk_score INTEGER DEFAULT 0,
                    final_score INTEGER DEFAULT 0,
                    FOREIGN KEY (company_id) REFERENCES companies (id),
                    UNIQUE(email, company_id)
                )
            ''')

            # Modern contacts table for new Contact model
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    domain TEXT NOT NULL,
                    name TEXT,
                    role TEXT,
                    company TEXT,
                    status TEXT DEFAULT 'unvalidated',
                    confidence_score REAL DEFAULT 0.0,
                    overall_score REAL DEFAULT 0.0,
                    persona_match TEXT,
                    source TEXT,
                    source_url TEXT,
                    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    validated_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Audit log for compliance tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    action TEXT NOT NULL,
                    source_url TEXT,
                    source_type TEXT,
                    legal_basis TEXT DEFAULT 'legitimate_interest',
                    purpose TEXT DEFAULT 'b2b_marketing',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    proof_note TEXT
                )
            ''')

            # Cache table for external API responses
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT UNIQUE NOT NULL,
                    cache_value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    access_count INTEGER DEFAULT 0
                )
            ''')

            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_companies_domain ON companies(domain)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_email ON emails(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_company ON emails(company_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_contacts_domain ON contacts(domain)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_email ON audit_log(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_key ON cache(cache_key)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at)')

            conn.commit()
            logger.info("Database initialized successfully")

    def add_contact(self, contact: Contact) -> bool:
        """Add a new contact to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT OR REPLACE INTO contacts
                    (email, domain, name, role, company, status, confidence_score,
                     overall_score, persona_match, source, source_url, extracted_at, validated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    contact.email,
                    contact.domain,
                    contact.name,
                    contact.role,
                    contact.company,
                    contact.status.value if isinstance(contact.status, ContactStatus) else contact.status,
                    contact.confidence_score,
                    contact.overall_score,
                    contact.persona_match,
                    contact.source,
                    contact.source_url,
                    contact.extracted_at.isoformat() if contact.extracted_at else datetime.now().isoformat(),
                    contact.validated_at.isoformat() if contact.validated_at else None
                ))

                conn.commit()

                # Log audit action
                self._log_audit_action(
                    email=contact.email,
                    action='contact_added',
                    source_url=contact.source_url or '',
                    source_type=contact.source or '',
                    proof_note=f"Contact {contact.email} added from {contact.source or 'unknown'}"
                )

                return True

        except Exception as e:
            logger.error(f"Failed to add contact {contact.email}: {e}")
            return False

    def get_contact(self, email: str) -> Optional[Contact]:
        """Retrieve a contact by email address"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute('SELECT * FROM contacts WHERE email = ?', (email,))
                row = cursor.fetchone()

                if row:
                    return Contact.from_dict(dict(row))

        except Exception as e:
            logger.error(f"Failed to get contact {email}: {e}")

        return None

    def get_all_contacts(self) -> List[Contact]:
        """Retrieve all contacts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute('SELECT * FROM contacts ORDER BY extracted_at DESC')
                rows = cursor.fetchall()

                return [Contact.from_dict(dict(row)) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get all contacts: {e}")
            return []

    def update_contact_status(self, email: str, status: ContactStatus) -> bool:
        """Update contact status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                status_value = status.value if isinstance(status, ContactStatus) else status

                cursor.execute('''
                    UPDATE contacts
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE email = ?
                ''', (status_value, email))

                if cursor.rowcount > 0:
                    conn.commit()

                    # Log audit action
                    self._log_audit_action(
                        email=email,
                        action='status_updated',
                        proof_note=f"Status updated to {status_value}"
                    )

                    return True

        except Exception as e:
            logger.error(f"Failed to update contact status for {email}: {e}")

        return False

    def get_contact_stats(self) -> Dict[str, Any]:
        """Get contact statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                stats = {}

                # Total contacts
                cursor.execute('SELECT COUNT(*) FROM contacts')
                stats['total'] = cursor.fetchone()[0]

                # Contacts by status
                cursor.execute('''
                    SELECT status, COUNT(*)
                    FROM contacts
                    GROUP BY status
                ''')
                stats['by_status'] = dict(cursor.fetchall())

                # Average scores
                cursor.execute('''
                    SELECT
                        AVG(confidence_score) as avg_confidence,
                        AVG(overall_score) as avg_overall
                    FROM contacts
                    WHERE confidence_score > 0
                ''')
                result = cursor.fetchone()
                stats['avg_confidence_score'] = result[0] if result[0] else 0.0
                stats['avg_overall_score'] = result[1] if result[1] else 0.0

                # Top domains
                cursor.execute('''
                    SELECT domain, COUNT(*) as count
                    FROM contacts
                    GROUP BY domain
                    ORDER BY count DESC
                    LIMIT 10
                ''')
                stats['top_domains'] = dict(cursor.fetchall())

                return stats

        except Exception as e:
            logger.error(f"Failed to get contact stats: {e}")
            return {'total': 0, 'by_status': {}, 'avg_confidence_score': 0.0, 'avg_overall_score': 0.0, 'top_domains': {}}

    def cleanup_old_data(self, days: int = 30) -> Tuple[int, int]:
        """Clean up old data based on retention policy"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cutoff_date = datetime.now() - timedelta(days=days)
                cutoff_str = cutoff_date.isoformat()

                # Clean up old contacts (those that haven't been updated recently)
                cursor.execute('''
                    DELETE FROM contacts
                    WHERE updated_at < ? AND status IN ('invalid', 'bounced')
                ''', (cutoff_str,))
                contacts_deleted = cursor.rowcount

                # Clean up old audit entries
                cursor.execute('''
                    DELETE FROM audit_log
                    WHERE timestamp < ?
                ''', (cutoff_str,))
                audit_deleted = cursor.rowcount

                # Clean up expired cache
                cursor.execute('DELETE FROM cache WHERE expires_at <= CURRENT_TIMESTAMP')

                conn.commit()

                logger.info(f"Cleanup completed: {contacts_deleted} contacts, {audit_deleted} audit entries removed")
                return contacts_deleted, audit_deleted

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return 0, 0

    def store_seeds(self, queries: List[str], persona: str, sector: str, geography: str):
        """Store search seed queries."""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for query in queries:
                cursor.execute('''
                    INSERT OR IGNORE INTO seeds (query, persona, sector, geography)
                    VALUES (?, ?, ?, ?)
                ''', (query, persona, sector, geography))

            conn.commit()
            logger.info(f"Stored {len(queries)} seed queries")

    def store_company(self, company_data: Dict[str, Any]) -> int:
        """Store company data and return company ID."""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            technologies_json = json.dumps(company_data.get('technologies', []))

            cursor.execute('''
                INSERT OR REPLACE INTO companies
                (name, domain, url, industry, size_category, country, technologies,
                 source_url, source_type, credibility_score, retrieved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_data.get('name', ''),
                company_data.get('domain', ''),
                company_data.get('url', ''),
                company_data.get('industry', ''),
                company_data.get('size_category', ''),
                company_data.get('country', ''),
                technologies_json,
                company_data.get('source_url', ''),
                company_data.get('source_type', ''),
                company_data.get('credibility_score', 50),
                company_data.get('retrieved_at', datetime.now().isoformat())
            ))

            company_id = cursor.lastrowid
            conn.commit()

            # Log for audit trail
            self._log_audit_action(
                email='',
                action='company_stored',
                source_url=company_data.get('source_url', ''),
                source_type=company_data.get('source_type', ''),
                proof_note=f"Company {company_data.get('name', '')} stored from {company_data.get('source_url', '')}"
            )

            return company_id

    def store_email(self, email_data: Dict[str, Any]) -> int:
        """Store email data and return email ID."""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO emails
                (email, role, confidence, context, company_id, source_url, source_type,
                 extracted_at, validation_status, mx_valid, deliverable, risk_score, final_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                email_data.get('email', ''),
                email_data.get('role', ''),
                email_data.get('confidence', 0.0),
                email_data.get('context', ''),
                email_data.get('company_id'),
                email_data.get('source_url', ''),
                email_data.get('source_type', ''),
                email_data.get('extracted_at', datetime.now().isoformat()),
                email_data.get('validation_status', 'pending'),
                email_data.get('mx_valid'),
                email_data.get('deliverable'),
                email_data.get('risk_score', 0),
                email_data.get('final_score', 0)
            ))

            email_id = cursor.lastrowid
            conn.commit()

            # Log for audit trail
            self._log_audit_action(
                email=email_data.get('email', ''),
                action='email_extracted',
                source_url=email_data.get('source_url', ''),
                source_type=email_data.get('source_type', ''),
                proof_note=f"Email extracted with confidence {email_data.get('confidence', 0.0)}"
            )

            return email_id

    def get_companies(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve stored companies."""

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = 'SELECT * FROM companies ORDER BY retrieved_at DESC'
            if limit:
                query += f' LIMIT {limit}'

            cursor.execute(query)
            companies = []

            for row in cursor.fetchall():
                company = dict(row)
                company['technologies'] = json.loads(company['technologies'] or '[]')
                companies.append(company)

            return companies

    def get_emails(self, min_score: int = 0, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve stored emails with optional filtering."""

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT e.*, c.name as company_name, c.domain,
                       c.sector as industry, c.location as country
                FROM emails e
                LEFT JOIN companies c ON e.company_id = c.id
                WHERE e.risk_score >= ?
                ORDER BY e.confidence_score DESC, e.created_at DESC
            '''

            if limit:
                query += f' LIMIT {limit}'

            cursor.execute(query, (min_score,))
            return [dict(row) for row in cursor.fetchall()]

    def update_email_validation(self, email_id: int, validation_data: Dict[str, Any]):
        """Update email validation results."""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE emails
                SET validation_status = ?, mx_valid = ?, deliverable = ?, risk_score = ?
                WHERE id = ?
            ''', (
                validation_data.get('status', 'validated'),
                validation_data.get('mx_valid', False),
                validation_data.get('deliverable', False),
                validation_data.get('risk_score', 0),
                email_id
            ))

            conn.commit()

    def update_email_score(self, email_id: int, score: int):
        """Update email final score."""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('UPDATE emails SET final_score = ? WHERE id = ?', (score, email_id))
            conn.commit()

    def _log_audit_action(self, email: str, action: str, source_url: str = '',
                         source_type: str = '', proof_note: str = ''):
        """Log action for audit trail."""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO audit_log (email, action, source_url, source_type, proof_note)
                VALUES (?, ?, ?, ?, ?)
            ''', (email, action, source_url, source_type, proof_note))

            conn.commit()

    def get_audit_log(self, email: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieve audit log entries."""

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if email:
                cursor.execute('''
                    SELECT * FROM audit_log
                    WHERE email = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (email, limit))
            else:
                cursor.execute('''
                    SELECT * FROM audit_log
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def cache_set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """Store value in cache with TTL."""

        cache_key = hashlib.md5(key.encode()).hexdigest()
        cache_value = json.dumps(value) if not isinstance(value, str) else value
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO cache (cache_key, cache_value, expires_at)
                VALUES (?, ?, ?)
            ''', (cache_key, cache_value, expires_at.isoformat()))

            conn.commit()

    def cache_get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache if not expired."""

        cache_key = hashlib.md5(key.encode()).hexdigest()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT cache_value FROM cache
                WHERE cache_key = ? AND expires_at > CURRENT_TIMESTAMP
            ''', (cache_key,))

            result = cursor.fetchone()
            if result:
                # Update access count
                cursor.execute('''
                    UPDATE cache SET access_count = access_count + 1
                    WHERE cache_key = ?
                ''', (cache_key,))
                conn.commit()

                try:
                    return json.loads(result[0])
                except json.JSONDecodeError:
                    return result[0]

        return None

    def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries."""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('DELETE FROM cache WHERE expires_at <= CURRENT_TIMESTAMP')
            removed_count = cursor.rowcount
            conn.commit()

            return removed_count

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            stats = {}

            # Count records in each table
            tables = ['seeds', 'companies', 'emails', 'audit_log', 'cache']
            for table in tables:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                stats[f'{table}_count'] = cursor.fetchone()[0]

            # Email validation stats
            cursor.execute('''
                SELECT validation_status, COUNT(*)
                FROM emails
                GROUP BY validation_status
            ''')
            stats['email_validation_breakdown'] = dict(cursor.fetchall())

            # Score distribution
            cursor.execute('''
                SELECT
                    CASE
                        WHEN final_score >= 80 THEN 'high'
                        WHEN final_score >= 60 THEN 'medium'
                        ELSE 'low'
                    END as score_category,
                    COUNT(*)
                FROM emails
                GROUP BY score_category
            ''')
            stats['score_distribution'] = dict(cursor.fetchall())

            return stats

    def export_to_csv(self, output_path: str, min_score: int = 0):
        """Export emails to CSV format."""

        import csv

        emails = self.get_emails(min_score=min_score)

        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            if not emails:
                return 0

            fieldnames = emails[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for email in emails:
                writer.writerow(email)

        return len(emails)

    def close(self):
        """Close database connections (if needed for cleanup)."""
        # SQLite connections are automatically closed when context managers exit
        pass

    def _get_connection(self):
        """Get database connection (for compatibility)."""
        return sqlite3.connect(self.db_path)
