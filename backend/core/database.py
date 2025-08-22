"""
Database Configuration - Simplified SQLite
Basic database setup for OSINT system
"""

import sqlite3
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

from .config import get_settings

settings = get_settings()

# Simple database connection
class DatabaseManager:
    """Simple SQLite database manager"""

    def __init__(self):
        self.db_path = self._get_db_path()
        self._ensure_db_directory()

    def _get_db_path(self) -> str:
        """Get database path from settings"""
        if settings.DATABASE_URL.startswith("sqlite://"):
            return settings.DATABASE_URL.replace("sqlite://", "")
        return "data/osint_cache.db"

    def _ensure_db_directory(self):
        """Ensure database directory exists"""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute query and return results"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute insert and return last row id"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid


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
    """

    try:
        with db_manager.get_connection() as conn:
            conn.executescript(comprehensive_schema)
            conn.commit()

            # Insert sample data if sources table is empty
            cursor = conn.execute("SELECT COUNT(*) FROM sources")
            if cursor.fetchone()[0] == 0:
                await _insert_sample_sources(conn)

        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating tables: {e}")

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
        with db_manager.get_connection() as conn:
            conn.execute("SELECT 1")
            return True
    except Exception:
        return False


# Compatibility functions for FastAPI dependencies
async def get_db_session():
    """Get database session (mock for compatibility)"""
    return db_manager


# Mock AsyncSession for compatibility
class MockAsyncSession:
    """Mock async session for compatibility"""
    def __init__(self, db_manager):
        self.db_manager = db_manager

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass