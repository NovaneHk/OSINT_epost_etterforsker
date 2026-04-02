#!/usr/bin/env bash
# generate_env.sh — Generate production secrets and write .env.production
# Usage: ./scripts/generate_env.sh [domain] [admin_email]
set -euo pipefail

DOMAIN="${1:-example.com}"
ADMIN_EMAIL="${2:-admin@${DOMAIN}}"
ENV_FILE=".env.production"

echo "[generate_env] Writing ${ENV_FILE} ..."

# Generate cryptographically random secrets
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
DB_PASSWORD=$(openssl rand -hex 16)
FIRST_ADMIN_PASSWORD=$(openssl rand -base64 16 | tr -d '=/+' | head -c 20)

cat > "${ENV_FILE}" <<EOF
# Auto-generated production environment — $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# DO NOT commit this file to source control.

ENVIRONMENT=production
DEBUG=false

# Security — change only if you know what you are doing
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=sqlite:///./data/osint_cache.db
DB_PASSWORD=${DB_PASSWORD}

# CORS / Hosts — update to match your domain
CORS_ORIGINS=https://${DOMAIN}
ALLOWED_HOSTS=${DOMAIN}

# Admin seed (first run only)
SEED_DEFAULT_ADMIN=true
DEFAULT_ADMIN_EMAIL=${ADMIN_EMAIL}
DEFAULT_ADMIN_PASSWORD=${FIRST_ADMIN_PASSWORD}
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_FULL_NAME=System Administrator

# GDPR (set to true to require consent before lead creation)
GDPR_REQUIRE_CONSENT=false

# Optional integrations (fill in as needed)
# REDIS_URL=redis://localhost:6379/0
# HIBP_API_KEY=
# N8N_WEBHOOK_URL=
# N8N_API_KEY=
# SALESFORCE_INSTANCE_URL=
# SALESFORCE_CLIENT_ID=
# SALESFORCE_CLIENT_SECRET=
# HUBSPOT_ACCESS_TOKEN=
# M365_TENANT_ID=
# M365_CLIENT_ID=
# M365_CLIENT_SECRET=
EOF

echo "[generate_env] Done. First admin password: ${FIRST_ADMIN_PASSWORD}"
echo "[generate_env] IMPORTANT: save this password — it will not be shown again."
echo "[generate_env] ${ENV_FILE} written."
