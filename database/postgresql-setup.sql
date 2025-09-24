-- OSINT E-post Etterforsker - PostgreSQL Production Database Setup
-- This script sets up the production database with proper users, permissions, and configuration

-- Create database (run as postgres superuser)
-- CREATE DATABASE osint_db;

-- Create application user with limited privileges
CREATE USER osint_user WITH ENCRYPTED PASSWORD 'secure_password_change_in_production';

-- Grant necessary privileges
GRANT CONNECT ON DATABASE osint_db TO osint_user;
GRANT USAGE ON SCHEMA public TO osint_user;
GRANT CREATE ON SCHEMA public TO osint_user;

-- Create tables with proper ownership
\c osint_db

-- Ensure osint_user owns the public schema for migrations
ALTER SCHEMA public OWNER TO osint_user;

-- Grant sequence privileges for auto-incrementing IDs
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO osint_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO osint_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO osint_user;

-- Grant table privileges
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO osint_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO osint_user;

-- Create read-only user for reporting/analytics
CREATE USER osint_readonly WITH ENCRYPTED PASSWORD 'readonly_password_change_in_production';
GRANT CONNECT ON DATABASE osint_db TO osint_readonly;
GRANT USAGE ON SCHEMA public TO osint_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO osint_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO osint_readonly;

-- Performance optimizations
-- Enable UUID extension for better ID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for faster text searching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable btree_gin for better indexing
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Create custom functions for OSINT operations
-- Function to calculate lead score based on multiple factors
CREATE OR REPLACE FUNCTION calculate_lead_score(
    email_verified BOOLEAN,
    social_found BOOLEAN,
    company_verified BOOLEAN,
    bounced BOOLEAN
) RETURNS INTEGER AS $$
BEGIN
    DECLARE
        score INTEGER := 0;
    BEGIN
        IF email_verified THEN score := score + 40; END IF;
        IF social_found THEN score := score + 20; END IF;
        IF company_verified THEN score := score + 30; END IF;
        IF bounced THEN score := score - 50; END IF;

        -- Ensure score is within valid range
        IF score < 0 THEN score := 0; END IF;
        IF score > 100 THEN score := 100; END IF;

        RETURN score;
    END;
END;
$$ LANGUAGE plpgsql;

-- Function to update lead scores automatically
CREATE OR REPLACE FUNCTION update_lead_scores() RETURNS TRIGGER AS $$
BEGIN
    NEW.score := calculate_lead_score(
        NEW.email_verified,
        NEW.social_profiles IS NOT NULL AND jsonb_array_length(NEW.social_profiles) > 0,
        NEW.company IS NOT NULL AND length(NEW.company) > 0,
        NEW.bounced
    );
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Performance monitoring views
CREATE OR REPLACE VIEW lead_statistics AS
SELECT
    COUNT(*) as total_leads,
    COUNT(*) FILTER (WHERE status = 'verified') as verified_leads,
    COUNT(*) FILTER (WHERE status = 'pending') as pending_leads,
    COUNT(*) FILTER (WHERE bounced = true) as bounced_leads,
    AVG(score) as average_score,
    COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') as leads_this_week,
    COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') as leads_this_month
FROM leads;

CREATE OR REPLACE VIEW campaign_performance AS
SELECT
    c.id,
    c.name,
    c.status,
    COUNT(l.id) as total_leads,
    COUNT(l.id) FILTER (WHERE l.status = 'verified') as verified_leads,
    AVG(l.score) as average_score,
    c.created_at,
    c.updated_at
FROM campaigns c
LEFT JOIN leads l ON l.campaign_id = c.id
GROUP BY c.id, c.name, c.status, c.created_at, c.updated_at;

-- Database maintenance functions
CREATE OR REPLACE FUNCTION cleanup_old_logs() RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete logs older than 90 days
    DELETE FROM search_run_logs
    WHERE created_at < CURRENT_DATE - INTERVAL '90 days';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    -- Update statistics
    ANALYZE search_run_logs;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create maintenance schedule (requires pg_cron extension in production)
-- SELECT cron.schedule('cleanup-logs', '0 2 * * 0', 'SELECT cleanup_old_logs();');

-- Backup function for critical data
CREATE OR REPLACE FUNCTION backup_critical_data() RETURNS TEXT AS $$
DECLARE
    backup_name TEXT;
BEGIN
    backup_name := 'osint_backup_' || to_char(CURRENT_TIMESTAMP, 'YYYY_MM_DD_HH24_MI_SS');

    -- This would typically call external backup tools
    -- For now, just return the backup name that would be created
    RETURN backup_name;
END;
$$ LANGUAGE plpgsql;

-- Security functions
CREATE OR REPLACE FUNCTION log_data_access(
    table_name TEXT,
    operation TEXT,
    user_id UUID DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    -- Log data access for audit purposes
    INSERT INTO audit_logs (table_name, operation, user_id, timestamp)
    VALUES (table_name, operation, user_id, CURRENT_TIMESTAMP);
EXCEPTION
    WHEN OTHERS THEN
        -- Don't fail the main operation if logging fails
        NULL;
END;
$$ LANGUAGE plpgsql;

-- Performance monitoring
CREATE OR REPLACE VIEW database_performance AS
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation,
    most_common_vals,
    most_common_freqs
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY tablename, attname;

-- Connection monitoring
CREATE OR REPLACE VIEW active_connections AS
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    state_change,
    query
FROM pg_stat_activity
WHERE state != 'idle'
AND datname = current_database();

-- Grant access to monitoring views
GRANT SELECT ON lead_statistics TO osint_user, osint_readonly;
GRANT SELECT ON campaign_performance TO osint_user, osint_readonly;
GRANT SELECT ON database_performance TO osint_readonly;
GRANT SELECT ON active_connections TO osint_readonly;

-- Create audit log table if it doesn't exist
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(255) NOT NULL,
    operation VARCHAR(50) NOT NULL,
    user_id UUID,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    details JSONB
);

-- Grant audit log access
GRANT INSERT ON audit_logs TO osint_user;
GRANT SELECT ON audit_logs TO osint_readonly;

-- Set up database configuration for optimal performance
-- (These should be set in postgresql.conf in production)
/*
-- Connection settings
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

-- WAL settings for durability
wal_level = replica
max_wal_senders = 3
wal_keep_segments = 32

-- Query optimization
random_page_cost = 1.1
effective_io_concurrency = 2

-- Logging for monitoring
log_min_duration_statement = 1000
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
*/

-- Final message
DO $$
BEGIN
    RAISE NOTICE 'OSINT PostgreSQL database setup completed successfully!';
    RAISE NOTICE 'Users created: osint_user, osint_readonly';
    RAISE NOTICE 'Extensions enabled: uuid-ossp, pg_trgm, btree_gin';
    RAISE NOTICE 'Custom functions and views created for OSINT operations';
    RAISE NOTICE 'Remember to change default passwords in production!';
END $$;