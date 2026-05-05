"""
Database Management System
Handles SQLite database operations for caching and storage
"""

import sqlite3
import json
import hashlib
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

from dataclasses import dataclass, field

@dataclass
class AuditEntry:
    action: str
    entity_type: str
    entity_id: str
    user_id: str = "system"
    timestamp: Optional[str] = None
    details: Optional[dict] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class ContactStatus(Enum):
    """Enumeration of contact statuses"""
    UNVALIDATED = "unvalidated"
    VALIDATED = "validated"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    BOUNCED = "bounced"
    OPTED_OUT = "opted_out"
    INVALID = "invalid"


@dataclass
class Contact:
    email: str
    domain: str = ""
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
    sector: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if isinstance(self.status, str):
            try:
                self.status = ContactStatus(self.status)
            except ValueError:
                self.status = ContactStatus.UNVALIDATED
        now = datetime.now()
        if self.extracted_at is None:
            self.extracted_at = now
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Contact':
        """Create contact from dictionary"""
        def parse_dt(val):
            if val is None:
                return None
            if isinstance(val, datetime):
                return val
            try:
                return datetime.fromisoformat(str(val))
            except (ValueError, TypeError):
                return None

        contact = cls(
            email=data['email'],
            domain=data.get('domain', ''),
            name=data.get('name'),
            role=data.get('role'),
            company=data.get('company'),
            status=data.get('status', 'unvalidated'),
            confidence_score=data.get('confidence_score', 0.0),
            overall_score=data.get('overall_score', 0.0),
            persona_match=data.get('persona_match'),
            source=data.get('source'),
            source_url=data.get('source_url'),
            sector=data.get('sector'),
            extracted_at=parse_dt(data.get('extracted_at')),
            validated_at=parse_dt(data.get('validated_at')),
            created_at=parse_dt(data.get('created_at')) or parse_dt(data.get('extracted_at')),
            updated_at=parse_dt(data.get('updated_at')) or parse_dt(data.get('extracted_at')),
        )

        return contact

class DatabaseManager:
    """Manages SQLite database operations for the OSINT system."""

    def __init__(self, db_path: str = "data/osint_cache.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    @contextmanager
    def _connect(self):
        """Context manager that opens, yields, commits and *closes* a connection."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self):
        """Public method to initialize database (for testing compatibility)"""
        self._init_database()

    def _init_database(self):
        """Initialize database with required tables."""

        with self._connect() as conn:
            cursor = conn.cursor()

            # Use DELETE journal mode (not WAL) to avoid file-lock issues on Windows
            cursor.execute('PRAGMA journal_mode=DELETE')

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
                    sector TEXT,
                    status TEXT DEFAULT 'unvalidated',
                    confidence_score REAL DEFAULT 0.0,
                    overall_score REAL DEFAULT 0.0,
                    persona_match TEXT,
                    source TEXT,
                    source_url TEXT,
                    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    validated_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Mirror leads table — backend API reads from this table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT,
                    company TEXT,
                    domain TEXT,
                    job_title TEXT,
                    confidence_score REAL DEFAULT 0.0,
                    verification_status TEXT DEFAULT 'unverified',
                    source_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Audit log for compliance tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL DEFAULT 'contact',
                    entity_id TEXT NOT NULL DEFAULT '',
                    user_id TEXT NOT NULL DEFAULT 'system',
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Migrate audit_log: add missing columns for older databases
            existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(audit_log)").fetchall()}
            if 'entity_type' not in existing_cols:
                cursor.execute("ALTER TABLE audit_log ADD COLUMN entity_type TEXT NOT NULL DEFAULT 'contact'")
            if 'entity_id' not in existing_cols:
                cursor.execute("ALTER TABLE audit_log ADD COLUMN entity_id TEXT NOT NULL DEFAULT ''")
            if 'user_id' not in existing_cols:
                cursor.execute("ALTER TABLE audit_log ADD COLUMN user_id TEXT NOT NULL DEFAULT 'system'")

            # Migrate companies: add missing columns for older databases
            companies_cols = {row[1] for row in cursor.execute("PRAGMA table_info(companies)").fetchall()}
            if 'retrieved_at' not in companies_cols:
                cursor.execute("ALTER TABLE companies ADD COLUMN retrieved_at TIMESTAMP")

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
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_key ON cache(cache_key)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at)')

            conn.commit()
            logger.info("Database initialized successfully")

    def add_contact(self, contact: Contact) -> bool:
        """Add a new contact to the database"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()

                now = datetime.now().isoformat()
                cursor.execute('''
                    INSERT OR REPLACE INTO contacts
                    (email, domain, name, role, company, sector, status, confidence_score,
                     overall_score, persona_match, source, source_url, extracted_at,
                     validated_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    contact.email,
                    contact.domain,
                    contact.name,
                    contact.role,
                    contact.company,
                    contact.sector,
                    contact.status.value if isinstance(contact.status, ContactStatus) else contact.status,
                    contact.confidence_score,
                    contact.overall_score,
                    contact.persona_match,
                    contact.source,
                    contact.source_url,
                    contact.extracted_at.isoformat() if contact.extracted_at else now,
                    contact.validated_at.isoformat() if contact.validated_at else None,
                    contact.created_at.isoformat() if contact.created_at else now,
                    now,
                ))

                # Sync to leads table so the backend API can see pipeline data
                status_val = contact.status.value if isinstance(contact.status, ContactStatus) else (contact.status or '')
                if status_val == ContactStatus.VALIDATED.value:
                    verification_status = 'verified'
                elif status_val in (ContactStatus.BOUNCED.value, ContactStatus.INVALID.value):
                    verification_status = 'invalid'
                else:
                    verification_status = 'unverified'

                cursor.execute('''
                    INSERT OR REPLACE INTO leads
                    (email, name, company, domain, job_title, confidence_score,
                     verification_status, source_url, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    contact.email,
                    contact.name,
                    contact.company,
                    contact.domain,
                    contact.role,
                    contact.confidence_score,
                    verification_status,
                    contact.source_url,
                    contact.created_at.isoformat() if contact.created_at else now,
                    now,
                ))

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to add contact {contact.email}: {e}")
            return False

    def get_contact(self, email: str) -> Optional[Contact]:
        """Retrieve a contact by email address"""
        try:
            with self._connect() as conn:
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
            with self._connect() as conn:
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
            with self._connect() as conn:
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
            with self._connect() as conn:
                cursor = conn.cursor()

                cursor.execute('SELECT COUNT(*) FROM contacts')
                total = cursor.fetchone()[0]

                cursor.execute('''SELECT status, COUNT(*) FROM contacts GROUP BY status''')
                by_status = dict(cursor.fetchall())

                return {
                    'total': total,
                    'validated': by_status.get('validated', 0),
                    'bounced': by_status.get('bounced', 0),
                    'unvalidated': by_status.get('unvalidated', 0),
                    'contacted': by_status.get('contacted', 0),
                    'responded': by_status.get('responded', 0),
                    'opted_out': by_status.get('opted_out', 0),
                    'invalid': by_status.get('invalid', 0),
                    'by_status': by_status,
                }

        except Exception as e:
            logger.error(f"Failed to get contact stats: {e}")
            return {'total': 0, 'validated': 0, 'bounced': 0, 'unvalidated': 0,
                    'contacted': 0, 'responded': 0, 'opted_out': 0, 'invalid': 0, 'by_status': {}}

    def get_contacts_by_status(self, status: ContactStatus) -> List[Contact]:
        """Get contacts filtered by status"""
        try:
            status_value = status.value if isinstance(status, ContactStatus) else status
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM contacts WHERE status = ?', (status_value,))
                return [Contact.from_dict(dict(row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get contacts by status: {e}")
            return []

    def get_contacts_by_domain(self, domain: str) -> List[Contact]:
        """Get contacts filtered by domain"""
        try:
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM contacts WHERE domain = ?', (domain,))
                return [Contact.from_dict(dict(row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get contacts by domain: {e}")
            return []

    def search_contacts(self, query: str) -> List[Contact]:
        """Search contacts by name, email, or company"""
        try:
            like_query = f'%{query}%'
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM contacts
                    WHERE email LIKE ? OR name LIKE ? OR company LIKE ?
                ''', (like_query, like_query, like_query))
                return [Contact.from_dict(dict(row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to search contacts: {e}")
            return []

    def add_audit_entry(self, entry: AuditEntry) -> bool:
        """Add an audit log entry"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO audit_log (action, entity_type, entity_id, user_id, details, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    entry.action,
                    entry.entity_type,
                    entry.entity_id,
                    entry.user_id,
                    json.dumps(entry.details) if entry.details else None,
                    entry.timestamp or datetime.now().isoformat(),
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to add audit entry: {e}")
            return False

    def get_audit_entries(self, limit: int = 100) -> List[AuditEntry]:
        """Get audit log entries ordered by timestamp descending"""
        try:
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?
                ''', (limit,))
                entries = []
                for row in cursor.fetchall():
                    d = dict(row)
                    details = None
                    if d.get('details'):
                        try:
                            details = json.loads(d['details'])
                        except (ValueError, TypeError):
                            details = d['details']
                    entries.append(AuditEntry(
                        action=d['action'],
                        entity_type=d.get('entity_type', 'contact'),
                        entity_id=d.get('entity_id', ''),
                        user_id=d.get('user_id', 'system'),
                        timestamp=d.get('timestamp'),
                        details=details,
                    ))
                return entries
        except Exception as e:
            logger.error(f"Failed to get audit entries: {e}")
            return []

    def get_kpi_stats(self) -> Dict[str, Any]:
        """Get KPI metrics for dashboard (SQLite implementation)"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                
                # Calculate date 7 days ago
                seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()

                # Leads 7d
                cursor.execute('SELECT COUNT(*) FROM contacts WHERE extracted_at >= ?', (seven_days_ago,))
                leads_7d = cursor.fetchone()[0]

                # Hits 7d (Audit log)
                cursor.execute('SELECT COUNT(*) FROM audit_log WHERE timestamp >= ?', (seven_days_ago,))
                hits_7d = cursor.fetchone()[0]

                # Conversion rate
                cursor.execute('SELECT COUNT(*) FROM contacts')
                total = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM contacts WHERE status = 'validated'")
                validated = cursor.fetchone()[0]
                conversion_rate = (validated / total * 100) if total > 0 else 0.0

                # Exports 7d
                cursor.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'export' AND timestamp >= ?", (seven_days_ago,))
                exports_7d = cursor.fetchone()[0]

                # Sources
                cursor.execute('SELECT COUNT(DISTINCT source) FROM contacts')
                total_sources = cursor.fetchone()[0]

                return {
                    "leads7d": leads_7d,
                    "hits7d": hits_7d,
                    "conversion_rate": round(conversion_rate, 1),
                    "exports7d": exports_7d,
                    "total_sources": total_sources,
                    "active_sources": total_sources
                }
        except Exception as e:
            logger.error(f"Failed to get KPI stats: {e}")
            return {
                "leads7d": 0,
                "hits7d": 0,
                "conversion_rate": 0.0,
                "exports7d": 0,
                "total_sources": 0,
                "active_sources": 0
            }

    def get_recent_leads(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get recent leads for the dashboard (SQLite implementation)"""
        try:
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT * FROM contacts 
                    ORDER BY extracted_at DESC 
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
                
                rows = cursor.fetchall()
                leads = []
                for row in rows:
                    data = dict(row)
                    lead = {
                        "id": str(data.get('id', '')),
                        "email": data.get('email'),
                        "name": data.get('name'),
                        "company": data.get('company'),
                        "title": data.get('role'),
                        "location": "Unknown",
                        "tags": [data.get('source')] if data.get('source') else [],
                        "score": data.get('overall_score'),
                        "sourceIds": [data.get('source')] if data.get('source') else [],
                        "createdAt": data.get('extracted_at'),
                        "updatedAt": data.get('updated_at')
                    }
                    leads.append(lead)
                return leads
        except Exception as e:
            logger.error(f"Failed to get recent leads: {e}")
            return []

    def cleanup_old_data(self, days: int = 30) -> Tuple[int, int]:
        """Clean up old data based on retention policy"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()

                cutoff_date = datetime.now() - timedelta(days=days)
                cutoff_str = cutoff_date.isoformat()

                # Clean up old contacts regardless of status.
                # The maintained tests expect stale contacts to be removed even
                # if they were inserted with the default unvalidated status.
                cursor.execute('''
                    DELETE FROM contacts
                    WHERE updated_at < ?
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

        with self._connect() as conn:
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

        with self._connect() as conn:
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

        with self._connect() as conn:
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

        with self._connect() as conn:
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

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT e.*, c.name as company_name, c.domain,
                       c.industry as industry, c.country as country
                FROM emails e
                LEFT JOIN companies c ON e.company_id = c.id
                WHERE e.risk_score >= ?
                ORDER BY e.confidence DESC, e.extracted_at DESC
            '''

            if limit:
                query += f' LIMIT {limit}'

            cursor.execute(query, (min_score,))
            return [dict(row) for row in cursor.fetchall()]

    def update_email_validation(self, email_id: int, validation_data: Dict[str, Any]):
        """Update email validation results."""

        with self._connect() as conn:
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

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute('UPDATE emails SET final_score = ? WHERE id = ?', (score, email_id))
            conn.commit()

    def _log_audit_action(self, email: str, action: str, source_url: str = '',
                         source_type: str = '', proof_note: str = ''):
        """Log action for audit trail."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO audit_log (action, entity_type, entity_id, user_id, details)
                    VALUES (?, ?, ?, ?, ?)
                ''', (action, 'contact', email, 'system',
                      json.dumps({'source_url': source_url, 'source_type': source_type, 'note': proof_note})))
                conn.commit()
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")

    def get_audit_log(self, email: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieve audit log entries (legacy method)."""
        try:
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if email:
                    cursor.execute('''
                        SELECT * FROM audit_log
                        WHERE entity_id = ?
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
        except Exception as e:
            logger.error(f"Failed to get audit log: {e}")
            return []

    def cache_set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """Store value in cache with TTL."""

        cache_key = hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()  # nosec B324
        cache_value = json.dumps(value) if not isinstance(value, str) else value
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO cache (cache_key, cache_value, expires_at)
                VALUES (?, ?, ?)
            ''', (cache_key, cache_value, expires_at.isoformat()))

            conn.commit()

    def cache_get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache if not expired."""

        cache_key = hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()  # nosec B324

        with self._connect() as conn:
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

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute('DELETE FROM cache WHERE expires_at <= CURRENT_TIMESTAMP')
            removed_count = cursor.rowcount
            conn.commit()

            return removed_count

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""

        with self._connect() as conn:
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
        """Close database connections and release file handles."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('PRAGMA journal_mode=DELETE')
            conn.close()
        except Exception:
            pass

    def __del__(self):
        """Ensure file handles are released on garbage collection."""
        import gc
        gc.collect()

    def _get_connection(self):
        """Get database connection (for compatibility)."""
        return sqlite3.connect(self.db_path)

