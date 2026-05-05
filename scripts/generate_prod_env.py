#!/usr/bin/env python3
"""
Generate a production-ready .env file with secure random secrets.

Usage:
    python scripts/generate_prod_env.py [--output .env.production]

The generated file contains placeholder comments where human decisions
are required (DATABASE_URL, domain names, API keys, etc.).
"""

import argparse
import secrets
import sys
from datetime import datetime
from pathlib import Path


def generate_secret(length: int = 48) -> str:
    return secrets.token_urlsafe(length)


def generate_password(length: int = 24) -> str:
    """Generate a password that meets the backend validator requirements:
    at least one uppercase, one lowercase, one digit."""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.isupper() for c in pwd)
            and any(c.islower() for c in pwd)
            and any(c.isdigit() for c in pwd)
        ):
            return pwd


def main():
    parser = argparse.ArgumentParser(description="Generate production .env file")
    parser.add_argument(
        "--output",
        default=".env.production",
        help="Output file path (default: .env.production)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing file without prompting",
    )
    args = parser.parse_args()

    output_path = Path(args.output)

    if output_path.exists() and not args.force:
        answer = input(f"{output_path} already exists. Overwrite? [y/N]: ").strip().lower()
        if answer != "y":
            print("Aborted.")
            sys.exit(0)

    secret_key = generate_secret(48)
    jwt_secret = generate_secret(48)
    admin_password = generate_password(24)
    redis_password = generate_secret(32)
    db_password = generate_secret(24)

    content = f"""\
# =============================================================================
# OSINT B2B Email System — Production Environment Configuration
# Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
#
# IMPORTANT: Keep this file SECRET. Never commit it to version control.
# Add .env.production to .gitignore if not already present.
# =============================================================================

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# ---------------------------------------------------------------------------
# Security — AUTO-GENERATED SECRETS (do not share)
# ---------------------------------------------------------------------------
SECRET_KEY={secret_key}
JWT_SECRET_KEY={jwt_secret}
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ---------------------------------------------------------------------------
# Database (PostgreSQL — replace with your actual connection details)
# ---------------------------------------------------------------------------
# Format: postgresql://USER:PASSWORD@HOST:PORT/DBNAME
DATABASE_URL=postgresql://osint_user:{db_password}@localhost:5432/osint_db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=osint_db
DB_USER=osint_user
DB_PASSWORD={db_password}

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
REDIS_URL=redis://:{redis_password}@localhost:6379
REDIS_PASSWORD={redis_password}
REDIS_PORT=6379

# ---------------------------------------------------------------------------
# Allowed hosts / CORS (replace with your actual domain)
# ---------------------------------------------------------------------------
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# ---------------------------------------------------------------------------
# Default admin account (used only if SEED_DEFAULT_ADMIN=true, first run)
# ---------------------------------------------------------------------------
SEED_DEFAULT_ADMIN=true
DEFAULT_ADMIN_EMAIL=admin@your-domain.com
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD={admin_password}
DEFAULT_ADMIN_FULL_NAME=System Administrator

# ---------------------------------------------------------------------------
# Sample data seeding — disable in production
# ---------------------------------------------------------------------------
SEED_SAMPLE_DATA=false

# ---------------------------------------------------------------------------
# GDPR
# ---------------------------------------------------------------------------
GDPR_REQUIRE_CONSENT=true
GDPR_RETENTION_DAYS=365

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# ---------------------------------------------------------------------------
# API documentation (admin-only; leave disabled unless needed)
# ---------------------------------------------------------------------------
ENABLE_ADMIN_DOCS=false
# ADMIN_DOCS_TOKEN=<generate-another-secret-if-you-enable-above>

# ---------------------------------------------------------------------------
# External OSINT integrations (optional — leave blank to disable)
# ---------------------------------------------------------------------------
HIBP_API_KEY=
SPIDERFOOT_URL=
SPIDERFOOT_API_KEY=
INTELOWL_URL=
INTELOWL_API_KEY=

# ---------------------------------------------------------------------------
# CRM / automation integrations (optional)
# ---------------------------------------------------------------------------
SALESFORCE_INSTANCE_URL=
SALESFORCE_CLIENT_ID=
SALESFORCE_CLIENT_SECRET=
HUBSPOT_ACCESS_TOKEN=
M365_TENANT_ID=
M365_CLIENT_ID=
M365_CLIENT_SECRET=
N8N_WEBHOOK_URL=
N8N_API_KEY=

# ---------------------------------------------------------------------------
# NovaNexus (optional)
# ---------------------------------------------------------------------------
NOVANEXUS_API_URL=
NOVANEXUS_API_KEY=
NOVANEXUS_CAMPAIGN_ID=

# ---------------------------------------------------------------------------
# Frontend (Next.js)
# Replace localhost with your actual domain/IP for production deploys.
# ---------------------------------------------------------------------------
NEXT_PUBLIC_API_URL=https://your-domain.com
NEXT_PUBLIC_WS_URL=wss://your-domain.com/ws
"""

    output_path.write_text(content, encoding="utf-8")

    print(f"\n[OK] Generated: {output_path}")
    print("\n[!] ACTION REQUIRED - review and replace these placeholders:")
    print("   - DATABASE_URL / DB_* - set your real PostgreSQL credentials")
    print("   - ALLOWED_HOSTS / CORS_ORIGINS - set your actual domain")
    print("   - DEFAULT_ADMIN_EMAIL - set admin email")
    print("   - NEXT_PUBLIC_API_URL / NEXT_PUBLIC_WS_URL - set your domain")
    print("\nGenerated secrets (already written to file):")
    print(f"   SECRET_KEY:          {secret_key[:12]}...")
    print(f"   JWT_SECRET_KEY:      {jwt_secret[:12]}...")
    print(f"   DEFAULT_ADMIN_PASSWORD: {admin_password[:6]}...")
    print(f"   DB_PASSWORD:         {db_password[:8]}...")
    print(f"   REDIS_PASSWORD:      {redis_password[:8]}...")


if __name__ == "__main__":
    main()
