"""MFA (TOTP) management endpoints for the OSINT system."""

import io
import base64
import json
import secrets
from datetime import datetime
from typing import Annotated, List

import pyotp
import qrcode

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.core.database import DatabaseManager
from backend.core.dependencies import AuthenticatedUser, DatabaseSession, get_current_active_user
from backend.core.security import jwt_manager, password_hash


router = APIRouter(prefix="/auth/mfa", tags=["MFA"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    qr_code_base64: str  # PNG PNG encoded as base64


class MFAActivateRequest(BaseModel):
    secret: str       # the secret shown during setup
    code: str         # 6-digit TOTP code to confirm


class MFADisableRequest(BaseModel):
    code: str         # current TOTP code OR a backup code


class MFABackupCodesResponse(BaseModel):
    backup_codes: List[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_qr_base64(provisioning_uri: str) -> str:
    img = qrcode.make(provisioning_uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _verify_code_or_backup(db: DatabaseManager, user_id: str, code: str) -> bool:
    rows = db.execute_query("SELECT mfa_secret, mfa_backup_codes FROM users WHERE id = ?", (user_id,))
    if not rows:
        return False
    row = rows[0]
    # Try TOTP first
    totp = pyotp.TOTP(row["mfa_secret"] or "")
    if totp.verify(code, valid_window=1):
        return True
    # Try backup codes
    raw = row.get("mfa_backup_codes") or "[]"
    try:
        codes: List[str] = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        codes = []
    if code in codes:
        # Consume the backup code (one-time use)
        codes.remove(code)
        db.execute_write(
            "UPDATE users SET mfa_backup_codes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(codes), user_id),
        )
        return True
    return False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/setup", response_model=MFASetupResponse, summary="Generate TOTP secret for MFA setup")
async def mfa_setup(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_active_user)],
    db: DatabaseSession,
):
    """Generate a new TOTP secret and QR code for the authenticated user.
    The user must call /activate with a valid code to enable MFA.
    """
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name="OSINT Etterforsker",
    )
    qr_b64 = _generate_qr_base64(provisioning_uri)
    return MFASetupResponse(
        secret=secret,
        provisioning_uri=provisioning_uri,
        qr_code_base64=qr_b64,
    )


@router.post("/activate", summary="Activate MFA after verifying TOTP code")
async def mfa_activate(
    payload: MFAActivateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_active_user)],
    db: DatabaseSession,
):
    """Activate MFA for the current user by verifying a TOTP code against the provided secret."""
    totp = pyotp.TOTP(payload.secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid TOTP code")

    db.execute_write(
        "UPDATE users SET mfa_secret = ?, mfa_enabled = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (payload.secret, current_user.id),
    )
    return {"detail": "MFA activated successfully"}


@router.post("/disable", summary="Disable MFA using current TOTP code or backup code")
async def mfa_disable(
    payload: MFADisableRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_active_user)],
    db: DatabaseSession,
):
    """Disable MFA for the current user. Requires verification of a current TOTP code."""
    if not _verify_code_or_backup(db, current_user.id, payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")

    db.execute_write(
        "UPDATE users SET mfa_secret = NULL, mfa_enabled = 0, mfa_backup_codes = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (current_user.id,),
    )
    return {"detail": "MFA disabled"}


@router.post("/backup-codes", response_model=MFABackupCodesResponse, summary="Regenerate backup codes")
async def mfa_backup_codes(
    payload: MFADisableRequest,  # reuse — just needs a code field
    current_user: Annotated[AuthenticatedUser, Depends(get_current_active_user)],
    db: DatabaseSession,
):
    """Generate 8 new single-use backup codes. Existing codes are replaced."""
    if not _verify_code_or_backup(db, current_user.id, payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")

    new_codes = [secrets.token_hex(4).upper() for _ in range(8)]
    db.execute_write(
        "UPDATE users SET mfa_backup_codes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (json.dumps(new_codes), current_user.id),
    )
    return MFABackupCodesResponse(backup_codes=new_codes)
