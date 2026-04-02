"""
PostgreSQL Database Manager
Enterprise-grade database management using SQLAlchemy
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from .database import Contact, ContactStatus

logger = logging.getLogger(__name__)

class PostgresDatabaseManager:
    """Manages PostgreSQL database operations for the OSINT system."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_pre_ping=True
        )
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        self._verify_connection()

    def _verify_connection(self):
        """Verify database connection and schema"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("Successfully connected to PostgreSQL database")
                
                # Check if tables exist, if not, we might need to initialize
                inspector = inspect(self.engine)
                tables = inspector.get_table_names()
                if "contacts" not in tables:
                    logger.warning("Tables not found in PostgreSQL. Please ensure init script ran.")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def get_kpi_stats(self) -> Dict[str, Any]:
        """Get KPI metrics for dashboard"""
        session = self.Session()
        try:
            # Calculate date 7 days ago
            seven_days_ago = datetime.now() - timedelta(days=7)
            
            # Leads in last 7 days
            result = session.execute(text("""
                SELECT COUNT(*) FROM contacts 
                WHERE extracted_at >= :date
            """), {"date": seven_days_ago}).scalar()
            leads_7d = result or 0

            # Total hits (using audit log as proxy for activity)
            result = session.execute(text("""
                SELECT COUNT(*) FROM audit_log 
                WHERE timestamp >= :date
            """), {"date": seven_days_ago}).scalar()
            hits_7d = result or 0

            # Conversion rate (Validated / Total)
            total = session.execute(text("SELECT COUNT(*) FROM contacts")).scalar() or 0
            validated = session.execute(text("""
                SELECT COUNT(*) FROM contacts 
                WHERE status = 'validated'
            """)).scalar() or 0
            
            conversion_rate = (validated / total * 100) if total > 0 else 0.0

            # Exports (mock for now as we don't have an exports table yet, or check audit log)
            exports_7d = session.execute(text("""
                SELECT COUNT(*) FROM audit_log 
                WHERE action = 'export' AND timestamp >= :date
            """), {"date": seven_days_ago}).scalar() or 0

            # Sources
            total_sources = session.execute(text("""
                SELECT COUNT(DISTINCT source) FROM contacts
            """)).scalar() or 0

            return {
                "leads7d": leads_7d,
                "hits7d": hits_7d,
                "conversion_rate": round(conversion_rate, 1),
                "exports7d": exports_7d,
                "total_sources": total_sources,
                "active_sources": total_sources # Assuming all are active for now
            }
        except Exception as e:
            logger.error(f"Error fetching KPI stats: {e}")
            return {
                "leads7d": 0,
                "hits7d": 0,
                "conversion_rate": 0.0,
                "exports7d": 0,
                "total_sources": 0,
                "active_sources": 0
            }
        finally:
            session.close()

    def get_recent_leads(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get recent leads for the dashboard"""
        session = self.Session()
        try:
            result = session.execute(text("""
                SELECT * FROM contacts 
                ORDER BY extracted_at DESC 
                LIMIT :limit OFFSET :offset
            """), {"limit": limit, "offset": offset})
            
            leads = []
            for row in result:
                # Map row to dict
                lead = {
                    "id": str(row.id),
                    "email": row.email,
                    "name": row.name,
                    "company": row.company,
                    "title": row.role,
                    "location": "Unknown", # Not in DB yet
                    "tags": [row.source] if row.source else [],
                    "score": row.overall_score,
                    "sourceIds": [row.source] if row.source else [],
                    "createdAt": row.extracted_at.isoformat() if row.extracted_at else None,
                    "updatedAt": row.updated_at.isoformat() if hasattr(row, 'updated_at') and row.updated_at else None
                }
                leads.append(lead)
            return leads
        except Exception as e:
            logger.error(f"Error fetching recent leads: {e}")
            return []
        finally:
            session.close()
