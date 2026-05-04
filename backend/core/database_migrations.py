"""
OSINT E-post Etterforsker - Database Migration Utilities
Utility functions for managing database migrations with Alembic
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from backend.core.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseMigrationManager:
    """Manages database migrations using Alembic"""

    def __init__(self):
        self.settings = get_settings()
        self.alembic_cfg_path = Path(__file__).parent.parent / "alembic.ini"

    def get_alembic_config(self) -> Config:
        """Get Alembic configuration with current database URL"""
        alembic_cfg = Config(str(self.alembic_cfg_path))
        alembic_cfg.set_main_option("sqlalchemy.url", self.settings.database_url)
        return alembic_cfg

    def check_database_connection(self) -> bool:
        """Check if database connection is available"""
        try:
            engine = create_engine(self.settings.database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
        except OperationalError as e:
            logger.error(f"Database connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            return False

    def create_database_if_not_exists(self) -> bool:
        """Create database if it doesn't exist"""
        try:
            # Extract database name from URL
            db_url_parts = self.settings.database_url.split('/')
            db_name = db_url_parts[-1]
            base_url = '/'.join(db_url_parts[:-1]) + '/postgres'

            # Connect to postgres database to create our target database
            engine = create_engine(base_url)
            with engine.connect() as conn:
                conn.execute(text("COMMIT"))  # End any existing transaction

                # Check if database exists — db_name comes from the DATABASE_URL config,
                # not from user input; sanitise to identifier-safe characters as a defence.
                _safe_db_name = "".join(c for c in db_name if c.isalnum() or c == "_")
                if _safe_db_name != db_name:
                    raise ValueError(f"Unsafe database name: {db_name!r}")
                result = conn.execute(text(  # nosec B608
                    f"SELECT 1 FROM pg_database WHERE datname='{_safe_db_name}'"
                ))
                if not result.fetchone():
                    conn.execute(text(f"CREATE DATABASE {_safe_db_name}"))  # nosec B608
                    logger.info(f"Created database: {db_name}")
                else:
                    logger.info(f"Database already exists: {db_name}")

            return True
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            return False

    def get_current_revision(self) -> Optional[str]:
        """Get current database revision"""
        try:
            alembic_cfg = self.get_alembic_config()
            from alembic.script import ScriptDirectory
            from alembic.runtime.environment import EnvironmentContext
            from alembic import context

            script = ScriptDirectory.from_config(alembic_cfg)

            def get_rev(rev, context):
                return rev

            engine = create_engine(self.settings.database_url)
            with engine.connect() as connection:
                context.configure(connection=connection)
                with context.begin_transaction():
                    return context.get_current_revision()

        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            return None

    def get_head_revision(self) -> Optional[str]:
        """Get head revision from migration files"""
        try:
            alembic_cfg = self.get_alembic_config()
            from alembic.script import ScriptDirectory

            script = ScriptDirectory.from_config(alembic_cfg)
            return script.get_current_head()
        except Exception as e:
            logger.error(f"Failed to get head revision: {e}")
            return None

    def is_database_up_to_date(self) -> bool:
        """Check if database is up to date with latest migrations"""
        current = self.get_current_revision()
        head = self.get_head_revision()

        if current is None or head is None:
            return False

        return current == head

    def run_migrations(self, target_revision: str = "head") -> bool:
        """Run database migrations to specified revision"""
        try:
            if not self.check_database_connection():
                logger.error("Cannot run migrations: database connection failed")
                return False

            alembic_cfg = self.get_alembic_config()
            command.upgrade(alembic_cfg, target_revision)
            logger.info(f"Successfully migrated database to revision: {target_revision}")
            return True
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False

    def create_migration(self, message: str, autogenerate: bool = True) -> bool:
        """Create a new migration file"""
        try:
            alembic_cfg = self.get_alembic_config()
            command.revision(
                alembic_cfg,
                message=message,
                autogenerate=autogenerate
            )
            logger.info(f"Created new migration: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            return False

    def rollback_migration(self, target_revision: str = "-1") -> bool:
        """Rollback to previous migration"""
        try:
            alembic_cfg = self.get_alembic_config()
            command.downgrade(alembic_cfg, target_revision)
            logger.info(f"Successfully rolled back to revision: {target_revision}")
            return True
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def get_migration_history(self) -> list:
        """Get migration history"""
        try:
            alembic_cfg = self.get_alembic_config()
            from alembic.script import ScriptDirectory

            script = ScriptDirectory.from_config(alembic_cfg)
            revisions = []

            for revision in script.walk_revisions():
                revisions.append({
                    'revision': revision.revision,
                    'down_revision': revision.down_revision,
                    'description': revision.doc,
                    'create_date': getattr(revision.module, 'create_date', None)
                })

            return revisions
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            return []

    def initialize_database(self) -> bool:
        """Initialize database with all migrations"""
        try:
            logger.info("Initializing database...")

            # Create database if it doesn't exist
            if not self.create_database_if_not_exists():
                return False

            # Check connection
            if not self.check_database_connection():
                return False

            # Run migrations
            if not self.run_migrations():
                return False

            logger.info("Database initialization completed successfully")
            return True
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False

    async def initialize_database_async(self) -> bool:
        """Async version of database initialization"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.initialize_database
        )


# Convenience functions
def get_migration_manager() -> DatabaseMigrationManager:
    """Get database migration manager instance"""
    return DatabaseMigrationManager()


async def ensure_database_initialized() -> bool:
    """Ensure database is initialized and up to date"""
    manager = get_migration_manager()
    return await manager.initialize_database_async()


def create_migration_cli(message: str, autogenerate: bool = True) -> bool:
    """CLI function to create new migration"""
    manager = get_migration_manager()
    return manager.create_migration(message, autogenerate)


def run_migrations_cli(target_revision: str = "head") -> bool:
    """CLI function to run migrations"""
    manager = get_migration_manager()
    return manager.run_migrations(target_revision)


def rollback_migration_cli(target_revision: str = "-1") -> bool:
    """CLI function to rollback migrations"""
    manager = get_migration_manager()
    return manager.rollback_migration(target_revision)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python database_migrations.py <command> [args]")
        print("Commands:")
        print("  init                    - Initialize database with all migrations")
        print("  migrate [revision]      - Run migrations (default: head)")
        print("  rollback [revision]     - Rollback migrations (default: -1)")
        print("  create <message>        - Create new migration")
        print("  status                  - Show migration status")
        print("  history                 - Show migration history")
        sys.exit(1)

    command_name = sys.argv[1]
    manager = get_migration_manager()

    if command_name == "init":
        success = manager.initialize_database()
        sys.exit(0 if success else 1)

    elif command_name == "migrate":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        success = manager.run_migrations(revision)
        sys.exit(0 if success else 1)

    elif command_name == "rollback":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        success = manager.rollback_migration(revision)
        sys.exit(0 if success else 1)

    elif command_name == "create":
        if len(sys.argv) < 3:
            print("Error: Migration message is required")
            sys.exit(1)
        message = sys.argv[2]
        success = manager.create_migration(message)
        sys.exit(0 if success else 1)

    elif command_name == "status":
        current = manager.get_current_revision()
        head = manager.get_head_revision()
        up_to_date = manager.is_database_up_to_date()

        print(f"Current revision: {current}")
        print(f"Head revision: {head}")
        print(f"Up to date: {up_to_date}")

        if not up_to_date:
            print("Database needs migration!")

    elif command_name == "history":
        history = manager.get_migration_history()
        for revision in history:
            print(f"Revision: {revision['revision']}")
            print(f"  Down revision: {revision['down_revision']}")
            print(f"  Description: {revision['description']}")
            print(f"  Create date: {revision['create_date']}")
            print()

    else:
        print(f"Unknown command: {command_name}")
        sys.exit(1)