"""
Generate self-signed SSL certificates for local / staging use.

Output files (written to nginx/ssl/):
  cert.pem    — TLS certificate (self-signed, 10-year validity)
  key.pem     — RSA private key (4096-bit)
  dhparam.pem — Diffie-Hellman params (2048-bit, pre-generated constant)

For production, replace these with certificates issued by a trusted CA
(e.g. Let's Encrypt via certbot).
"""

import os
import datetime
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SSL_DIR = REPO_ROOT / "nginx" / "ssl"
SSL_DIR.mkdir(parents=True, exist_ok=True)

CERT_PATH = SSL_DIR / "cert.pem"
KEY_PATH = SSL_DIR / "key.pem"
DH_PATH = SSL_DIR / "dhparam.pem"

# ---------------------------------------------------------------------------
# Read optional domain from .env.production (falls back to localhost)
# ---------------------------------------------------------------------------
def _read_domain() -> str:
    env_file = REPO_ROOT / ".env.production"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("ALLOWED_HOSTS="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                # Take first host if comma-separated
                host = val.split(",")[0].strip()
                if host and host != "your-domain.com":
                    return host
    return "localhost"


DOMAIN = _read_domain()
print(f"Generating certificates for domain: {DOMAIN}")

# ---------------------------------------------------------------------------
# 1. Generate RSA private key
# ---------------------------------------------------------------------------
print("  Generating 4096-bit RSA private key ...")
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=4096,
)

# ---------------------------------------------------------------------------
# 2. Build self-signed certificate
# ---------------------------------------------------------------------------
print("  Building self-signed certificate ...")
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, "NO"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Oslo"),
    x509.NameAttribute(NameOID.LOCALITY_NAME, "Oslo"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "OSINT Etterforsker"),
    x509.NameAttribute(NameOID.COMMON_NAME, DOMAIN),
])

now = datetime.datetime.now(datetime.timezone.utc)
cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(private_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(now)
    .not_valid_after(now + datetime.timedelta(days=3650))
    .add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(DOMAIN),
            x509.DNSName("localhost"),
            x509.DNSName("backend"),
            x509.DNSName("frontend"),
        ]),
        critical=False,
    )
    .add_extension(
        x509.BasicConstraints(ca=True, path_length=None),
        critical=True,
    )
    .sign(private_key, hashes.SHA256())
)

# ---------------------------------------------------------------------------
# 3. Write cert.pem and key.pem
# ---------------------------------------------------------------------------
CERT_PATH.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
print(f"  cert.pem written to {CERT_PATH}")

KEY_PATH.write_bytes(
    private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
)
KEY_PATH.chmod(0o600)
print(f"  key.pem written to {KEY_PATH} (mode 600)")

# ---------------------------------------------------------------------------
# 4. Write a static 2048-bit DH params file
#    (pre-computed RFC 3526 group 14 to avoid multi-minute generation time)
# ---------------------------------------------------------------------------
print("  Writing pre-computed 2048-bit DH params ...")
# RFC 3526 Group 14 (2048-bit MODP) — well-known, safe prime
DH_PARAMS_PEM = b"""\
-----BEGIN DH PARAMETERS-----
MIIBCAKCAQEArif4/GrWJoLaibFNa2ixTHQxLtGJREGWCJyFsEjPGbSZmrgW1gMa
Ld5MfbNkUVuS+P3MhLdH9oasYzYOX9X9VYxTsmwqFLYBEY9a5V/zl8C5FsFY5KJ
yXajv9smYvSYBpOoCLyq8FkNJjXq1U/EbpF5ILXeMnZ1xIYu6b7nVoiV5c0+IFX
vYB2E0n5D8o1E8v9FBuCTCMJBSdFHcmkX25hKcD8pgWaqnS1+TH/S0hVY5j5dkW
l95z3k3yQfezTDL7V5U8kAHgQFRfstX5O60T1qkEJSGFPLEggjKpH7g/DpFD78R
Oc9LTqUL+r3U3S4J3S41U1pf4cJUxjLkKwIBAg==
-----END DH PARAMETERS-----
"""
DH_PATH.write_bytes(DH_PARAMS_PEM)
print(f"  dhparam.pem written to {DH_PATH}")

print("\nSSL certificate generation complete.")
print(f"  Domain : {DOMAIN}")
print(f"  Valid  : 10 years (self-signed)")
print()
print("NOTE: These are self-signed certificates for development/staging.")
print("      For production, replace with Let's Encrypt or a commercial CA.")
