#!/usr/bin/env bash
# setup_ssl.sh — Obtain a Let's Encrypt TLS certificate via certbot.
# Falls back to a self-signed certificate if certbot is unavailable (local dev).
#
# Usage: ./scripts/setup_ssl.sh <domain> <email>
#   domain  — public FQDN  (e.g. osint.example.com)
#   email   — contact email for Let's Encrypt notifications
set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-}"
SSL_DIR="nginx/ssl"
NGINX_CONF="nginx/nginx.conf"

if [[ -z "${DOMAIN}" || -z "${EMAIL}" ]]; then
    echo "Usage: $0 <domain> <email>"
    exit 1
fi

mkdir -p "${SSL_DIR}"

# ---------------------------------------------------------------------------
# Try certbot (production)
# ---------------------------------------------------------------------------
if command -v certbot &>/dev/null; then
    echo "[setup_ssl] certbot found — requesting Let's Encrypt certificate for ${DOMAIN} ..."
    certbot --nginx \
        -d "${DOMAIN}" \
        --non-interactive \
        --agree-tos \
        -m "${EMAIL}" \
        --redirect \
        || {
            echo "[setup_ssl] certbot failed — falling back to self-signed cert"
            _generate_self_signed
        }

    # Update nginx.conf cert paths to Let's Encrypt
    LE_CERT="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
    LE_KEY="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"
    sed -i "s|ssl_certificate .*;|ssl_certificate ${LE_CERT};|" "${NGINX_CONF}"
    sed -i "s|ssl_certificate_key .*;|ssl_certificate_key ${LE_KEY};|" "${NGINX_CONF}"
    echo "[setup_ssl] nginx.conf updated to use Let's Encrypt paths"

else
    echo "[setup_ssl] certbot not found — generating self-signed certificate for local dev ..."
    _generate_self_signed
fi

echo "[setup_ssl] SSL setup complete."

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
_generate_self_signed() {
    openssl req -x509 -newkey rsa:4096 \
        -keyout "${SSL_DIR}/key.pem" \
        -out    "${SSL_DIR}/cert.pem" \
        -days 365 \
        -nodes \
        -subj "/CN=${DOMAIN}" \
        2>/dev/null
    # Generate DH params only if not present
    if [[ ! -f "${SSL_DIR}/dhparam.pem" ]]; then
        openssl dhparam -out "${SSL_DIR}/dhparam.pem" 2048 2>/dev/null
    fi
    echo "[setup_ssl] Self-signed cert written to ${SSL_DIR}/"
}
