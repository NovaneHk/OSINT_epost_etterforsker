#!/usr/bin/env bash
# deploy.sh — Full production deployment orchestrator.
# Usage: ./scripts/deploy.sh <domain> <admin_email>
#
#   1. Generate .env.production with random secrets
#   2. Set up TLS certificate (certbot or self-signed)
#   3. Start all Docker Compose services
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

DOMAIN="${1:-}"
EMAIL="${2:-}"

if [[ -z "${DOMAIN}" || -z "${EMAIL}" ]]; then
    echo "Usage: $0 <domain> <admin_email>"
    echo " e.g.: $0 osint.example.com admin@example.com"
    exit 1
fi

cd "${PROJECT_ROOT}"

echo "======================================================"
echo " OSINT Etterforsker — Production Deploy"
echo " Domain : ${DOMAIN}"
echo " Email  : ${EMAIL}"
echo "======================================================"

# Step 1: Generate secrets
echo ""
echo "[deploy] Step 1/3 — Generating production secrets ..."
bash "${SCRIPT_DIR}/generate_env.sh" "${DOMAIN}" "${EMAIL}"

# Step 2: TLS certificate
echo ""
echo "[deploy] Step 2/3 — Setting up TLS ..."
bash "${SCRIPT_DIR}/setup_ssl.sh" "${DOMAIN}" "${EMAIL}"

# Step 3: Docker Compose
echo ""
echo "[deploy] Step 3/3 — Starting Docker services ..."
COMPOSE_FILE="docker-compose.prod.yml"
if [[ ! -f "${COMPOSE_FILE}" ]]; then
    COMPOSE_FILE="docker-compose.yml"
fi

docker compose -f "${COMPOSE_FILE}" --env-file .env.production up -d --build

echo ""
echo "[deploy] Deployment complete!"
echo "[deploy] Application available at: https://${DOMAIN}"
echo "[deploy] Check logs with: docker compose logs -f"
