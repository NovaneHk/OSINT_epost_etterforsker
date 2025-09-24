"""Initial database schema for OSINT E-post Etterforsker

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-01-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all initial tables for OSINT E-post Etterforsker system"""

    # Create UUID extension for PostgreSQL
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('username', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('full_name', sa.String(100), nullable=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('role', sa.String(20), nullable=False, default='investigator'),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('profile_image_url', sa.String(500), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('login_count', sa.Integer(), nullable=False, default=0),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("role IN ('admin', 'investigator', 'analyst', 'viewer')", name='users_role_check')
    )

    # Create sources table
    op.create_table(
        'sources',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('name', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('source_type', sa.String(20), nullable=False, index=True),
        sa.Column('url', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='active'),
        sa.Column('is_premium', sa.Boolean(), nullable=False, default=False),
        sa.Column('requires_api_key', sa.Boolean(), nullable=False, default=False),
        sa.Column('api_key', sa.String(255), nullable=True),
        sa.Column('configuration', sa.JSON(), nullable=True),
        sa.Column('capabilities', sa.ARRAY(sa.String), nullable=True),
        sa.Column('rate_limit_per_hour', sa.Integer(), nullable=True),
        sa.Column('requests_made', sa.Integer(), nullable=False, default=0),
        sa.Column('successful_requests', sa.Integer(), nullable=False, default=0),
        sa.Column('failed_requests', sa.Integer(), nullable=False, default=0),
        sa.Column('last_request_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('average_response_time', sa.Float(), nullable=True),
        sa.Column('is_healthy', sa.Boolean(), nullable=False, default=True),
        sa.Column('health_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("source_type IN ('website', 'social_media', 'api', 'database', 'search_engine', 'directory')", name='sources_type_check'),
        sa.CheckConstraint("status IN ('active', 'inactive', 'maintenance', 'deprecated')", name='sources_status_check')
    )

    # Create campaigns table
    op.create_table(
        'campaigns',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('name', sa.String(100), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='draft'),
        sa.Column('priority', sa.String(10), nullable=False, default='medium'),
        sa.Column('target_criteria', sa.JSON(), nullable=True),
        sa.Column('search_parameters', sa.JSON(), nullable=True),
        sa.Column('automation_rules', sa.JSON(), nullable=True),
        sa.Column('target_count', sa.Integer(), nullable=True),
        sa.Column('contacted_count', sa.Integer(), nullable=False, default=0),
        sa.Column('response_count', sa.Integer(), nullable=False, default=0),
        sa.Column('conversion_count', sa.Integer(), nullable=False, default=0),
        sa.Column('budget_allocated', sa.Numeric(10, 2), nullable=True),
        sa.Column('budget_used', sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paused_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('assigned_to', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("status IN ('draft', 'active', 'paused', 'completed', 'cancelled')", name='campaigns_status_check'),
        sa.CheckConstraint("priority IN ('low', 'medium', 'high', 'urgent')", name='campaigns_priority_check'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ondelete='SET NULL')
    )

    # Create search_runs table
    op.create_table(
        'search_runs',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('name', sa.String(100), nullable=False, index=True),
        sa.Column('run_type', sa.String(20), nullable=False, default='manual'),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('priority', sa.String(10), nullable=False, default='medium'),
        sa.Column('sources', sa.ARRAY(sa.String), nullable=True),
        sa.Column('search_terms', sa.JSON(), nullable=True),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('configuration', sa.JSON(), nullable=True),
        sa.Column('progress', sa.Float(), nullable=False, default=0.0),
        sa.Column('current_step', sa.String(100), nullable=True),
        sa.Column('total_steps', sa.Integer(), nullable=True),
        sa.Column('leads_found', sa.Integer(), nullable=False, default=0),
        sa.Column('leads_verified', sa.Integer(), nullable=False, default=0),
        sa.Column('sources_processed', sa.Integer(), nullable=False, default=0),
        sa.Column('estimated_completion', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paused_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('results_summary', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('campaign_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("run_type IN ('manual', 'scheduled', 'automated')", name='search_runs_type_check'),
        sa.CheckConstraint("status IN ('pending', 'running', 'paused', 'completed', 'failed', 'cancelled')", name='search_runs_status_check'),
        sa.CheckConstraint("priority IN ('low', 'medium', 'high', 'urgent')", name='search_runs_priority_check'),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name='search_runs_progress_check'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='SET NULL')
    )

    # Create leads table
    op.create_table(
        'leads',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('first_name', sa.String(50), nullable=True),
        sa.Column('last_name', sa.String(50), nullable=True),
        sa.Column('company', sa.String(100), nullable=True, index=True),
        sa.Column('job_title', sa.String(100), nullable=True),
        sa.Column('department', sa.String(50), nullable=True),
        sa.Column('seniority_level', sa.String(20), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('linkedin_url', sa.String(500), nullable=True),
        sa.Column('twitter_url', sa.String(500), nullable=True),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('location', sa.String(100), nullable=True),
        sa.Column('country', sa.String(50), nullable=True),
        sa.Column('industry', sa.String(50), nullable=True, index=True),
        sa.Column('company_size', sa.String(20), nullable=True),
        sa.Column('annual_revenue', sa.String(20), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('quality_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('verification_status', sa.String(20), nullable=False, default='pending'),
        sa.Column('email_status', sa.String(20), nullable=False, default='unknown'),
        sa.Column('contact_status', sa.String(20), nullable=False, default='new'),
        sa.Column('tags', sa.ARRAY(sa.String), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('osint_data', sa.JSON(), nullable=True),
        sa.Column('enrichment_data', sa.JSON(), nullable=True),
        sa.Column('last_contacted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_response_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('contact_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('source_name', sa.String(100), nullable=True),
        sa.Column('source_url', sa.String(500), nullable=True),
        sa.Column('found_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('search_run_id', sa.String(36), nullable=True),
        sa.Column('campaign_id', sa.String(36), nullable=True),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('assigned_to', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("seniority_level IN ('entry', 'mid', 'senior', 'executive', 'c_level')", name='leads_seniority_check'),
        sa.CheckConstraint("verification_status IN ('pending', 'verified', 'invalid', 'bounced')", name='leads_verification_check'),
        sa.CheckConstraint("email_status IN ('unknown', 'valid', 'invalid', 'risky', 'deliverable', 'undeliverable')", name='leads_email_status_check'),
        sa.CheckConstraint("contact_status IN ('new', 'contacted', 'responded', 'converted', 'bounced', 'unsubscribed')", name='leads_contact_status_check'),
        sa.CheckConstraint("confidence_score >= 0 AND confidence_score <= 100", name='leads_confidence_check'),
        sa.CheckConstraint("quality_score >= 0 AND quality_score <= 100", name='leads_quality_check'),
        sa.ForeignKeyConstraint(['search_run_id'], ['search_runs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ondelete='SET NULL')
    )

    # Create exports table
    op.create_table(
        'exports',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('name', sa.String(100), nullable=False, index=True),
        sa.Column('export_type', sa.String(10), nullable=False, default='csv'),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('format_options', sa.JSON(), nullable=True),
        sa.Column('record_count', sa.Integer(), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('download_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_downloaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('progress', sa.Float(), nullable=False, default=0.0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("export_type IN ('csv', 'json', 'excel')", name='exports_type_check'),
        sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')", name='exports_status_check'),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name='exports_progress_check'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE')
    )

    # Create additional indexes for performance
    op.create_index('idx_users_email_active', 'users', ['email', 'is_active'])
    op.create_index('idx_users_role_active', 'users', ['role', 'is_active'])
    op.create_index('idx_leads_email_unique', 'leads', ['email'], unique=True)
    op.create_index('idx_leads_company_industry', 'leads', ['company', 'industry'])
    op.create_index('idx_leads_verification_status', 'leads', ['verification_status'])
    op.create_index('idx_leads_confidence_score', 'leads', ['confidence_score'])
    op.create_index('idx_sources_type_status', 'sources', ['source_type', 'status'])
    op.create_index('idx_campaigns_status_created_by', 'campaigns', ['status', 'created_by'])
    op.create_index('idx_search_runs_status_created_by', 'search_runs', ['status', 'created_by'])
    op.create_index('idx_exports_status_created_by', 'exports', ['status', 'created_by'])

    # Create updated_at trigger function for PostgreSQL
    op.execute("""
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    """)

    # Create triggers for all tables to auto-update updated_at
    tables = ['users', 'sources', 'campaigns', 'search_runs', 'leads', 'exports']
    for table in tables:
        op.execute(f"""
        CREATE TRIGGER update_{table}_updated_at
        BEFORE UPDATE ON {table}
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    """Drop all tables and related objects"""

    # Drop triggers
    tables = ['users', 'sources', 'campaigns', 'search_runs', 'leads', 'exports']
    for table in tables:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table}")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Drop tables in reverse order due to foreign key constraints
    op.drop_table('exports')
    op.drop_table('leads')
    op.drop_table('search_runs')
    op.drop_table('campaigns')
    op.drop_table('sources')
    op.drop_table('users')

    # Drop UUID extension
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')