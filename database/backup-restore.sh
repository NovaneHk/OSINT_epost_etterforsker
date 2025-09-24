#!/bin/bash

# OSINT E-post Etterforsker - PostgreSQL Backup and Restore Scripts
# Production-ready backup and restore functionality

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_NAME="${POSTGRES_DB:-osint_db}"
DB_USER="${POSTGRES_USER:-osint_user}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Function to log messages
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check PostgreSQL connection
check_connection() {
    log "Checking PostgreSQL connection..."

    if ! PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; then
        error "Cannot connect to PostgreSQL database"
        error "Host: $DB_HOST:$DB_PORT, Database: $DB_NAME, User: $DB_USER"
        exit 1
    fi

    success "Database connection verified"
}

# Function to create full backup
create_full_backup() {
    log "Creating full database backup..."

    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_file="$BACKUP_DIR/osint_full_backup_$timestamp.sql"
    local backup_compressed="$backup_file.gz"

    log "Backup file: $backup_file"

    # Create backup with custom format for better compression and restore options
    if PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --verbose \
        --no-owner \
        --no-acl \
        --format=custom \
        --file="$backup_file.custom"; then

        # Also create SQL format backup
        PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --verbose \
            --no-owner \
            --no-acl \
            --format=plain \
            --file="$backup_file"

        # Compress SQL backup
        gzip "$backup_file"

        success "Full backup created successfully"
        log "Custom format: $backup_file.custom"
        log "Compressed SQL: $backup_compressed"

        # Get backup size
        local custom_size=$(du -h "$backup_file.custom" | cut -f1)
        local sql_size=$(du -h "$backup_compressed" | cut -f1)
        success "Backup sizes: Custom=$custom_size, SQL=$sql_size"

        return 0
    else
        error "Backup creation failed"
        return 1
    fi
}

# Function to create schema-only backup
create_schema_backup() {
    log "Creating schema-only backup..."

    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local schema_file="$BACKUP_DIR/osint_schema_$timestamp.sql"

    if PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --schema-only \
        --verbose \
        --no-owner \
        --no-acl \
        --file="$schema_file"; then

        gzip "$schema_file"
        success "Schema backup created: $schema_file.gz"
        return 0
    else
        error "Schema backup failed"
        return 1
    fi
}

# Function to create data-only backup
create_data_backup() {
    log "Creating data-only backup..."

    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local data_file="$BACKUP_DIR/osint_data_$timestamp.sql"

    if PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --data-only \
        --verbose \
        --no-owner \
        --no-acl \
        --file="$data_file"; then

        gzip "$data_file"
        success "Data backup created: $data_file.gz"
        return 0
    else
        error "Data backup failed"
        return 1
    fi
}

# Function to restore from backup
restore_backup() {
    local backup_file="$1"

    if [ -z "$backup_file" ]; then
        error "No backup file specified"
        echo "Usage: $0 restore <backup_file>"
        return 1
    fi

    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        return 1
    fi

    warning "This will OVERWRITE the current database!"
    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        log "Restore cancelled"
        return 0
    fi

    log "Restoring database from: $backup_file"

    # Determine file type and restore accordingly
    if [[ "$backup_file" == *.custom ]]; then
        # Custom format restore
        if PGPASSWORD="$POSTGRES_PASSWORD" pg_restore \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --clean \
            --if-exists \
            --verbose \
            "$backup_file"; then
            success "Database restored successfully from custom format"
        else
            error "Restore failed"
            return 1
        fi
    elif [[ "$backup_file" == *.sql.gz ]]; then
        # Compressed SQL restore
        if gunzip -c "$backup_file" | PGPASSWORD="$POSTGRES_PASSWORD" psql \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME"; then
            success "Database restored successfully from compressed SQL"
        else
            error "Restore failed"
            return 1
        fi
    elif [[ "$backup_file" == *.sql ]]; then
        # Plain SQL restore
        if PGPASSWORD="$POSTGRES_PASSWORD" psql \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            -f "$backup_file"; then
            success "Database restored successfully from SQL file"
        else
            error "Restore failed"
            return 1
        fi
    else
        error "Unknown backup file format: $backup_file"
        return 1
    fi
}

# Function to clean old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."

    local deleted_count=0

    # Find and delete old backup files
    if find "$BACKUP_DIR" -name "osint_*_backup_*.sql*" -type f -mtime +$RETENTION_DAYS -print0 | while IFS= read -r -d '' file; do
        log "Deleting old backup: $(basename "$file")"
        rm "$file"
        ((deleted_count++))
    done; then
        success "Cleaned up $deleted_count old backup files"
    else
        warning "No old backup files found or cleanup failed"
    fi
}

# Function to list available backups
list_backups() {
    log "Available backups in $BACKUP_DIR:"
    echo

    if ls -la "$BACKUP_DIR"/osint_*backup*.* 2>/dev/null; then
        echo
        log "Backup sizes:"
        du -h "$BACKUP_DIR"/osint_*backup*.* 2>/dev/null || true
    else
        warning "No backup files found in $BACKUP_DIR"
    fi
}

# Function to verify backup integrity
verify_backup() {
    local backup_file="$1"

    if [ -z "$backup_file" ]; then
        error "No backup file specified"
        return 1
    fi

    log "Verifying backup integrity: $backup_file"

    if [[ "$backup_file" == *.custom ]]; then
        if pg_restore --list "$backup_file" > /dev/null 2>&1; then
            success "Custom backup file is valid"
            return 0
        else
            error "Custom backup file is corrupted"
            return 1
        fi
    elif [[ "$backup_file" == *.sql.gz ]]; then
        if gunzip -t "$backup_file" 2>/dev/null; then
            success "Compressed backup file is valid"
            return 0
        else
            error "Compressed backup file is corrupted"
            return 1
        fi
    elif [[ "$backup_file" == *.sql ]]; then
        if [ -r "$backup_file" ] && [ -s "$backup_file" ]; then
            success "SQL backup file is readable and not empty"
            return 0
        else
            error "SQL backup file is not readable or empty"
            return 1
        fi
    else
        error "Unknown backup file format"
        return 1
    fi
}

# Main script logic
case "${1:-}" in
    "full")
        check_connection
        create_full_backup
        cleanup_old_backups
        ;;
    "schema")
        check_connection
        create_schema_backup
        ;;
    "data")
        check_connection
        create_data_backup
        ;;
    "restore")
        check_connection
        restore_backup "$2"
        ;;
    "list")
        list_backups
        ;;
    "verify")
        verify_backup "$2"
        ;;
    "cleanup")
        cleanup_old_backups
        ;;
    *)
        echo "OSINT E-post Etterforsker - PostgreSQL Backup & Restore Tool"
        echo
        echo "Usage: $0 <command> [options]"
        echo
        echo "Commands:"
        echo "  full                 Create full database backup (schema + data)"
        echo "  schema               Create schema-only backup"
        echo "  data                 Create data-only backup"
        echo "  restore <file>       Restore database from backup file"
        echo "  list                 List available backup files"
        echo "  verify <file>        Verify backup file integrity"
        echo "  cleanup              Remove old backup files"
        echo
        echo "Environment Variables:"
        echo "  POSTGRES_DB          Database name (default: osint_db)"
        echo "  POSTGRES_USER        Database user (default: osint_user)"
        echo "  POSTGRES_PASSWORD    Database password (required)"
        echo "  POSTGRES_HOST        Database host (default: localhost)"
        echo "  POSTGRES_PORT        Database port (default: 5432)"
        echo "  BACKUP_DIR           Backup directory (default: ./backups)"
        echo "  BACKUP_RETENTION_DAYS Backup retention in days (default: 30)"
        echo
        echo "Examples:"
        echo "  $0 full              # Create full backup"
        echo "  $0 restore backup.sql.gz  # Restore from compressed backup"
        echo "  $0 list              # List all backups"
        exit 1
        ;;
esac