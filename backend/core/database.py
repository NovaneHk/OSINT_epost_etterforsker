"""
Database Configuration - Simplified SQLite
Basic database setup for OSINT system
"""

import sqlite3
import asyncio
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import uuid4

try:
    import psycopg
    from psycopg.rows import dict_row as _pg_dict_row
    _HAS_PSYCOPG = True
except ImportError:
    _HAS_PSYCOPG = False

from .config import get_settings

settings = get_settings()

# Database connection manager
class DatabaseManager:
    """Database manager supporting SQLite (development) and PostgreSQL (production)."""

    def __init__(self):
        db_url = settings.DATABASE_URL
        self._is_postgres = db_url.startswith("postgresql://") or db_url.startswith("postgres://")
        if self._is_postgres:
            if not _HAS_PSYCOPG:
                raise RuntimeError(
                    "psycopg is required for PostgreSQL connections. "
                    "Install it with: pip install psycopg"
                )
            self._pg_dsn = db_url
            self.db_path = None
        else:
            self.db_path = self._get_db_path()
            self._ensure_db_directory()
        self._write_lock = threading.Lock()

    def _get_db_path(self) -> str:
        """Get SQLite database path from settings."""
        db_url = settings.DATABASE_URL
        if db_url.startswith("sqlite:///"):
            return db_url[len("sqlite:///"):]
        if db_url.startswith("sqlite://"):
            return db_url[len("sqlite://"):]
        return "data/osint_cache.db"

    def _ensure_db_directory(self):
        """Ensure SQLite database directory exists."""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

    def _convert_query(self, query: str) -> str:
        """Convert SQLite ? placeholders to PostgreSQL %s when needed."""
        if self._is_postgres:
            return query.replace("?", "%s")
        return query

    def get_connection(self):
        """Get a raw database connection (sqlite3 or psycopg)."""
        if self._is_postgres:
            conn = psycopg.connect(self._pg_dsn)
            conn.autocommit = False
            return conn
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute SELECT query and return list of result dicts."""
        query = self._convert_query(query)
        if self._is_postgres:
            conn = psycopg.connect(self._pg_dsn)
            try:
                with conn.cursor(row_factory=_pg_dict_row) as cur:
                    cur.execute(query, params)
                    return [dict(row) for row in cur.fetchall()]
            finally:
                conn.close()
        else:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]

    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT and return the inserted row id."""
        query = self._convert_query(query)
        with self._write_lock:
            if self._is_postgres:
                conn = psycopg.connect(self._pg_dsn)
                try:
                    with conn.cursor() as cur:
                        if query.strip().upper().startswith("INSERT") and "RETURNING" not in query.upper():
                            pg_query = query.rstrip().rstrip(";") + " RETURNING id"
                            try:
                                cur.execute(pg_query, params)
                                row = cur.fetchone()
                                conn.commit()
                                return row[0] if row else 0
                            except Exception:
                                conn.rollback()
                                cur.execute(query, params)
                                conn.commit()
                                return 0
                        else:
                            cur.execute(query, params)
                            conn.commit()
                            return 0
                finally:
                    conn.close()
            else:
                with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    conn.commit()
                    return cursor.lastrowid

    def execute_write(self, query: str, params: tuple = ()) -> int:
        """Execute UPDATE/DELETE and return affected row count."""
        query = self._convert_query(query)
        with self._write_lock:
            if self._is_postgres:
                conn = psycopg.connect(self._pg_dsn)
                try:
                    with conn.cursor() as cur:
                        cur.execute(query, params)
                        conn.commit()
                        return cur.rowcount
                finally:
                    conn.close()
            else:
                with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    conn.commit()
                    return cursor.rowcount


# Global database manager
db_manager = DatabaseManager()

# Mock classes for compatibility
class Base:
    """Mock base class for compatibility"""
    pass

class metadata:
    """Mock metadata for compatibility"""
    @staticmethod
    def create_all():
        pass


async def create_tables():
    """Create all database tables if they don't exist"""
    if db_manager._is_postgres:
        print("PostgreSQL mode -- schema managed by Alembic. Run 'alembic upgrade head' to initialise.")
        return
    comprehensive_schema = """
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        name TEXT,
        company TEXT,
        domain TEXT,
        job_title TEXT,
        phone TEXT,
        linkedin_url TEXT,
        twitter_url TEXT,
        website TEXT,
        location TEXT,
        industry TEXT,
        company_size TEXT,
        revenue TEXT,
        technologies TEXT,
        confidence_score REAL DEFAULT 0.0,
        verification_status TEXT DEFAULT 'unverified',
        engagement_score REAL,
        last_contacted TIMESTAMP,
        source_id TEXT,
        source_url TEXT,
        notes TEXT,
        tags TEXT,
        custom_fields TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        type TEXT NOT NULL,
        url TEXT,
        description TEXT,
        configuration TEXT,
        status TEXT DEFAULT 'active',
        last_run TIMESTAMP,
        next_run TIMESTAMP,
        schedule_pattern TEXT,
        leads_count INTEGER DEFAULT 0,
        success_rate REAL DEFAULT 0.0,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        filter_criteria TEXT,
        status TEXT DEFAULT 'draft',
        leads_count INTEGER DEFAULT 0,
        target_count INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS exports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        filters TEXT,
        status TEXT DEFAULT 'pending',
        file_path TEXT,
        file_size INTEGER,
        leads_count INTEGER,
        progress REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        expires_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        source_ids TEXT,
        filters TEXT,
        status TEXT DEFAULT 'pending',
        progress REAL DEFAULT 0.0,
        leads_found INTEGER DEFAULT 0,
        leads_processed INTEGER DEFAULT 0,
        errors_count INTEGER DEFAULT 0,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        duration INTEGER,
        error_message TEXT,
        configuration TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS investigations (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        score REAL,
        findings TEXT DEFAULT '[]',
        error TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS playbooks (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        steps TEXT NOT NULL DEFAULT '[]',
        status TEXT DEFAULT 'draft',
        runs_count INTEGER DEFAULT 0,
        success_rate REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        value TEXT,
        category TEXT DEFAULT 'general',
        description TEXT,
        data_type TEXT DEFAULT 'string',
        is_sensitive BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE,
        full_name TEXT NOT NULL,
        hashed_password TEXT NOT NULL,
        role TEXT DEFAULT 'viewer',
        status TEXT DEFAULT 'active',
        is_active BOOLEAN DEFAULT 1,
        is_verified BOOLEAN DEFAULT 1,
        avatar_url TEXT,
        bio TEXT,
        company TEXT,
        department TEXT,
        job_title TEXT,
        phone TEXT,
        last_login TIMESTAMP,
        login_count INTEGER DEFAULT 0,
        failed_login_attempts INTEGER DEFAULT 0,
        password_changed_at TIMESTAMP,
        mfa_secret TEXT,
        mfa_enabled INTEGER DEFAULT 0,
        mfa_backup_codes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        action TEXT,
        resource_path TEXT,
        method TEXT,
        status_code INTEGER,
        ip_address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS lead_saved_views (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        filters TEXT NOT NULL,
        scope TEXT DEFAULT 'private',
        owner_user_id TEXT,
        owner_role TEXT,
        is_default BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS jwt_blacklist (
        jti TEXT PRIMARY KEY,
        revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at REAL NOT NULL
    );
    """

    try:
        with db_manager.get_connection() as conn:
            conn.executescript(comprehensive_schema)
            _ensure_settings_schema_compatibility(conn)
            _ensure_leads_schema_compatibility(conn)
            _ensure_mfa_columns(conn)
            _ensure_gdpr_columns(conn)
            _ensure_indexes(conn)
            _ensure_users_seeded(conn)
            conn.commit()

            # Insert sample data only when enabled (never in production by default)
            if settings.SEED_SAMPLE_DATA:
                cursor = conn.execute("SELECT COUNT(*) FROM sources")
                if cursor.fetchone()[0] == 0:
                    await _insert_sample_sources(conn)

        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating tables: {e}")


def _ensure_settings_schema_compatibility(conn):
    """Ensure legacy settings schema remains compatible with API expectations."""
    cursor = conn.execute("PRAGMA table_info(settings)")
    columns = {row[1] for row in cursor.fetchall()}

    if "is_public" not in columns:
        conn.execute("ALTER TABLE settings ADD COLUMN is_public BOOLEAN DEFAULT 1")

        if "is_sensitive" in columns:
            conn.execute(
                """
                UPDATE settings
                SET is_public = CASE
                    WHEN is_sensitive = 1 THEN 0
                    ELSE 1
                END
                WHERE is_public IS NULL
                """
            )

    cursor = conn.execute("PRAGMA table_info(lead_saved_views)")
    lead_saved_view_columns = {row[1] for row in cursor.fetchall()}

    if "scope" not in lead_saved_view_columns:
        conn.execute("ALTER TABLE lead_saved_views ADD COLUMN scope TEXT DEFAULT 'private'")
    if "owner_user_id" not in lead_saved_view_columns:
        conn.execute("ALTER TABLE lead_saved_views ADD COLUMN owner_user_id TEXT")
    if "owner_role" not in lead_saved_view_columns:
        conn.execute("ALTER TABLE lead_saved_views ADD COLUMN owner_role TEXT")


def _ensure_leads_schema_compatibility(conn):
    """Add columns expected by current API/indexes for legacy leads tables."""
    cursor = conn.execute("PRAGMA table_info(leads)")
    existing = {row[1] for row in cursor.fetchall()}

    required_columns = [
        ("domain", "TEXT"),
        ("location", "TEXT"),
        ("industry", "TEXT"),
        ("verification_status", "TEXT DEFAULT 'unverified'"),
        ("confidence_score", "REAL DEFAULT 0.0"),
    ]

    for column_name, column_definition in required_columns:
        if column_name not in existing:
            conn.execute(f"ALTER TABLE leads ADD COLUMN {column_name} {column_definition}")


def _ensure_mfa_columns(conn):
    """Add MFA columns to users table if missing (idempotent for existing DBs)."""
    cursor = conn.execute("PRAGMA table_info(users)")
    existing = {row[1] for row in cursor.fetchall()}
    for col, definition in [
        ("mfa_secret", "TEXT"),
        ("mfa_enabled", "INTEGER DEFAULT 0"),
        ("mfa_backup_codes", "TEXT"),
    ]:
        if col not in existing:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")


def _ensure_gdpr_columns(conn):
    """Add GDPR consent columns to leads table if missing."""
    cursor = conn.execute("PRAGMA table_info(leads)")
    existing = {row[1] for row in cursor.fetchall()}
    if "gdpr_consent" not in existing:
        conn.execute("ALTER TABLE leads ADD COLUMN gdpr_consent INTEGER DEFAULT 0")
    if "gdpr_consent_date" not in existing:
        conn.execute("ALTER TABLE leads ADD COLUMN gdpr_consent_date TIMESTAMP")


def _ensure_indexes(conn):
    """Create performance indexes and enable WAL mode."""
    # WAL pragma must run outside any active transaction
    conn.commit()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    index_specs = [
        ("contacts", ["email"], "CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email)"),
        ("contacts", ["domain"], "CREATE INDEX IF NOT EXISTS idx_contacts_domain ON contacts(domain)"),
        ("contacts", ["company"], "CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company)"),
        ("leads", ["email"], "CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email)"),
        ("leads", ["domain"], "CREATE INDEX IF NOT EXISTS idx_leads_domain ON leads(domain)"),
        ("leads", ["industry"], "CREATE INDEX IF NOT EXISTS idx_leads_industry ON leads(industry)"),
        ("leads", ["location"], "CREATE INDEX IF NOT EXISTS idx_leads_location ON leads(location)"),
        ("leads", ["verification_status", "confidence_score"], "CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(verification_status, confidence_score DESC)"),
        ("runs", ["status", "created_at"], "CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status, created_at DESC)"),
        ("investigations", ["email"], "CREATE INDEX IF NOT EXISTS idx_investigations_email ON investigations(email)"),
        ("investigations", ["status"], "CREATE INDEX IF NOT EXISTS idx_investigations_status ON investigations(status)"),
        ("audit_log", ["user_id", "created_at"], "CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id, created_at DESC)"),
        ("campaigns", ["status", "created_at"], "CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status, created_at DESC)"),
        ("campaigns", ["owner_id"], "CREATE INDEX IF NOT EXISTS idx_campaigns_owner ON campaigns(owner_id)"),
        ("exports", ["status", "created_at"], "CREATE INDEX IF NOT EXISTS idx_exports_status ON exports(status, created_at DESC)"),
        ("exports", ["created_by"], "CREATE INDEX IF NOT EXISTS idx_exports_creator ON exports(created_by)"),
        ("sources", ["status", "created_at"], "CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status, created_at DESC)"),
        ("playbooks", ["status"], "CREATE INDEX IF NOT EXISTS idx_playbooks_status ON playbooks(status)"),
        ("leads", ["created_at"], "CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at DESC)"),
        ("leads", ["company"], "CREATE INDEX IF NOT EXISTS idx_leads_company ON leads(company)"),
    ]

    for table_name, columns, statement in index_specs:
        if _columns_exist(conn, table_name, columns):
            conn.execute(statement)


def _table_exists(conn, table_name: str) -> bool:
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
    )
    return cursor.fetchone() is not None


def _columns_exist(conn, table_name: str, columns: List[str]) -> bool:
    """Return True only if table and all referenced columns exist."""
    if not _table_exists(conn, table_name):
        return False
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    return all(column in existing_columns for column in columns)


def _ensure_users_seeded(conn):
    """Create a default admin account for local development if needed."""
    cursor = conn.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    if user_count > 0 or not settings.SEED_DEFAULT_ADMIN:
        return

    from backend.core.security import password_hash

    conn.execute(
        """
        INSERT INTO users (
            id,
            email,
            username,
            full_name,
            hashed_password,
            role,
            status,
            is_active,
            is_verified,
            login_count
        ) VALUES (?, ?, ?, ?, ?, ?, 'active', 1, 1, 0)
        """,
        (
            str(uuid4()),
            settings.DEFAULT_ADMIN_EMAIL,
            settings.DEFAULT_ADMIN_USERNAME,
            settings.DEFAULT_ADMIN_FULL_NAME,
            password_hash.hash_password(settings.DEFAULT_ADMIN_PASSWORD),
            "admin",
        )
    )

async def _insert_sample_sources(conn):
    """Insert sample sources data"""
    sample_sources = [
        ("LinkedIn", "linkedin", "https://linkedin.com", "Professional networking platform", '{"search_depth": 3}', "active"),
        ("GitHub", "api", "https://api.github.com", "Code repository platform", '{"api_key": "required"}', "active"),
        ("Twitter", "twitter", "https://twitter.com", "Social media platform", '{"rate_limit": 300}', "active"),
        ("Google Search", "website", "https://google.com", "Web search engine", '{"safe_search": true}', "active"),
        ("Company Website", "website", "", "Direct company website scraping", '{"crawl_depth": 2}', "active"),
        ("Crunchbase", "api", "https://crunchbase.com", "Company information database", '{"api_key": "required"}', "inactive"),
        ("AngelList", "api", "https://angel.co", "Startup platform", '{"rate_limit": 100}', "active"),
        ("HackerNews", "website", "https://news.ycombinator.com", "Tech news platform", '{"scan_comments": true}', "active"),
        ("Reddit", "api", "https://reddit.com", "Social news platform", '{"subreddits": ["programming", "startups"]}', "inactive"),
        ("ProductHunt", "api", "https://producthunt.com", "Product discovery platform", '{"categories": ["tech"]}', "active")
    ]

    for source in sample_sources:
        conn.execute("""
            INSERT INTO sources (name, type, url, description, configuration, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, source)

    conn.commit()
    print("Sample sources inserted")


async def close_db_connections():
    """Close database connections (placeholder)"""
    pass


async def check_database_health() -> bool:
    """Check if database is accessible"""
    try:
        rows = db_manager.execute_query("SELECT 1 AS ok")
        return len(rows) > 0
    except Exception:
        return False


# Compatibility functions for FastAPI dependencies
async def get_db_session():
    """Get database manager for dependency injection."""
    return db_manager


# --- JWT blacklist helpers (used by security.py to persist revoked tokens) ---

def revoke_jti_in_db(jti: str, expires_at: float) -> None:
    """Persist a revoked JTI to the jwt_blacklist table."""
    import time
    try:
        if db_manager._is_postgres:
            conn = db_manager.get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO jwt_blacklist (jti, expires_at)
                        VALUES (%s, %s)
                        ON CONFLICT (jti) DO UPDATE SET expires_at = EXCLUDED.expires_at
                        """,
                        (jti, expires_at),
                    )
                    cur.execute("DELETE FROM jwt_blacklist WHERE expires_at < %s", (time.time(),))
                    conn.commit()
            finally:
                conn.close()
        else:
            with db_manager.get_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO jwt_blacklist (jti, expires_at) VALUES (?, ?)",
                    (jti, expires_at),
                )
                conn.commit()
                conn.execute("DELETE FROM jwt_blacklist WHERE expires_at < ?", (time.time(),))
                conn.commit()
    except Exception:
        pass  # Fail silently — in-memory cache in JWTManager still covers this session


def is_jti_revoked_in_db(jti: str) -> bool:
    """Check if a JTI has been revoked (persisted blacklist, survives restarts)."""
    try:
        import time
        rows = db_manager.execute_query(
            "SELECT jti FROM jwt_blacklist WHERE jti = ? AND expires_at > ?",
            (jti, time.time()),
        )
        return len(rows) > 0
    except Exception:
        return False  # Fail open — in-memory blacklist is the first check