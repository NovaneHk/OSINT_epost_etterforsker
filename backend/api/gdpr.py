"""
GDPR API — right-to-access (export) and right-to-erasure (delete) endpoints.
GDPR Articles 17 and 20.
"""

import logging
from fastapi import APIRouter, HTTPException, status

from backend.core.dependencies import PermissionDeps
from backend.core.gdpr_compliance import gdpr_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gdpr", tags=["gdpr"])


@router.get("/export/{email}", summary="Export all data for an email address")
async def export_data(
    email: str,
    current_user: PermissionDeps.SystemAdmin,
):
    """Return all stored personal data for *email* (GDPR Art. 20)."""
    gdpr_manager.log_request("export", email, current_user.id)
    data = gdpr_manager.export_lead_data(email)
    return data


@router.delete("/erase/{email}", summary="Erase personal data for an email address")
async def erase_data(
    email: str,
    current_user: PermissionDeps.SystemAdmin,
):
    """Anonymise and delete all personal data for *email* (GDPR Art. 17)."""
    gdpr_manager.log_request("erase", email, current_user.id)
    affected = gdpr_manager.erase_lead_data(email)
    if affected == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for {email}",
        )
    return {"erased_rows": affected, "email": email}
