"""External integrations API — n8n, Salesforce, HubSpot, Microsoft 365."""

import asyncio
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.core.config import get_settings
from backend.core.dependencies import AuthenticatedUser, DatabaseSession, PermissionDeps, get_current_active_user

router = APIRouter(prefix="/integrations", tags=["Integrations"])
settings = get_settings()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _require_env(*names: str, integration: str) -> None:
    """Raise 503 if any required env var is missing."""
    missing = [n for n in names if not getattr(settings, n, None)]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{integration} integration not configured. Missing: {', '.join(missing)}",
        )


# ---------------------------------------------------------------------------
# n8n
# ---------------------------------------------------------------------------

class N8NTriggerRequest(BaseModel):
    workflow: str
    data: Dict[str, Any] = {}


@router.post("/n8n/trigger", summary="Trigger an n8n workflow via webhook")
async def n8n_trigger(
    payload: N8NTriggerRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    _require_env("N8N_WEBHOOK_URL", integration="n8n")
    try:
        import sys
        sys.path.insert(0, ".")
        from automation.n8n_connector import N8NConnector  # type: ignore
        n8n_url = getattr(settings, "N8N_WEBHOOK_URL", "")
        n8n_api_key = getattr(settings, "N8N_API_KEY", None)
        connector = N8NConnector(base_url=n8n_url, api_key=n8n_api_key)
        result = connector.trigger_webhook(payload.workflow, payload.data)
        return {"success": True, "result": result}
    except ImportError:
        raise HTTPException(status_code=503, detail="n8n connector module not available")
    except Exception as exc:
        logger.exception("n8n trigger error")
        raise HTTPException(status_code=502, detail=f"n8n trigger failed: {exc}")


# ---------------------------------------------------------------------------
# Salesforce
# ---------------------------------------------------------------------------

class CRMPushRequest(BaseModel):
    lead_id: int


@router.post(
    "/salesforce/push",
    summary="Push a lead to Salesforce",
)
async def salesforce_push(payload: CRMPushRequest, db: DatabaseSession, current_user: PermissionDeps.CreateLeads):
    _require_env("SALESFORCE_CLIENT_ID", "SALESFORCE_CLIENT_SECRET", "SALESFORCE_INSTANCE_URL", integration="Salesforce")
    rows = db.execute_query("SELECT * FROM leads WHERE id = ?", (payload.lead_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead = rows[0]

    try:
        from integrations.salesforce_connector import SalesforceConnector  # type: ignore
        sf = SalesforceConnector(
            instance_url=getattr(settings, "SALESFORCE_INSTANCE_URL", ""),
            client_id=getattr(settings, "SALESFORCE_CLIENT_ID", ""),
            client_secret=getattr(settings, "SALESFORCE_CLIENT_SECRET", ""),
        )
        sf_id = await asyncio.to_thread(sf.push_lead, lead)
        return {"success": True, "salesforce_id": sf_id}
    except ImportError:
        raise HTTPException(status_code=503, detail="Salesforce connector not available")
    except Exception as exc:
        logger.exception("Salesforce push error")
        raise HTTPException(status_code=502, detail=f"Salesforce error: {exc}")


# ---------------------------------------------------------------------------
# HubSpot
# ---------------------------------------------------------------------------

@router.post(
    "/hubspot/push",
    summary="Push a lead to HubSpot",
)
async def hubspot_push(payload: CRMPushRequest, db: DatabaseSession, current_user: PermissionDeps.CreateLeads):
    _require_env("HUBSPOT_ACCESS_TOKEN", integration="HubSpot")
    rows = db.execute_query("SELECT * FROM leads WHERE id = ?", (payload.lead_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead = rows[0]

    try:
        from integrations.hubspot_connector import HubSpotConnector  # type: ignore
        hs = HubSpotConnector(access_token=getattr(settings, "HUBSPOT_ACCESS_TOKEN", ""))
        contact_id = await asyncio.to_thread(hs.create_or_update_contact, lead)
        return {"success": True, "hubspot_id": contact_id}
    except ImportError:
        raise HTTPException(status_code=503, detail="HubSpot connector not available")
    except Exception as exc:
        logger.exception("HubSpot push error")
        raise HTTPException(status_code=502, detail=f"HubSpot error: {exc}")


# ---------------------------------------------------------------------------
# Microsoft 365
# ---------------------------------------------------------------------------

@router.post(
    "/m365/sync",
    summary="Sync a lead to Microsoft 365 People",
)
async def m365_sync(payload: CRMPushRequest, db: DatabaseSession, current_user: PermissionDeps.CreateLeads):
    _require_env("M365_TENANT_ID", "M365_CLIENT_ID", "M365_CLIENT_SECRET", integration="Microsoft 365")
    rows = db.execute_query("SELECT * FROM leads WHERE id = ?", (payload.lead_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead = rows[0]

    try:
        from integrations.m365_connector import M365Connector  # type: ignore
        m365 = M365Connector(
            tenant_id=getattr(settings, "M365_TENANT_ID", ""),
            client_id=getattr(settings, "M365_CLIENT_ID", ""),
            client_secret=getattr(settings, "M365_CLIENT_SECRET", ""),
        )
        contact_id = await asyncio.to_thread(m365.add_or_update_contact, lead)
        return {"success": True, "m365_id": contact_id}
    except ImportError:
        raise HTTPException(status_code=503, detail="M365 connector not available")
    except Exception as exc:
        logger.exception("M365 sync error")
        raise HTTPException(status_code=502, detail=f"M365 error: {exc}")


# ---------------------------------------------------------------------------
# IntelOwl
# ---------------------------------------------------------------------------

class IntelOwlAnalyzeRequest(BaseModel):
    target: str
    scan_type: str = "email"  # email | domain | ip


@router.post("/intelowl/analyze", summary="Analyze a target with IntelOwl threat intelligence")
async def intelowl_analyze(
    payload: IntelOwlAnalyzeRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Submits *target* as an observable to IntelOwl. Requires IntelOwl running locally."""
    _require_env("INTELOWL_API_KEY", integration="IntelOwl")
    try:
        import sys
        sys.path.insert(0, ".")
        from integrations.intelowl_connector import IntelOwlConnector  # type: ignore
        io_url = getattr(settings, "INTELOWL_URL", "http://localhost:80")
        io_key = getattr(settings, "INTELOWL_API_KEY", None)
        connector = IntelOwlConnector(api_url=io_url, api_key=io_key)
        result = await connector.search(payload.target, search_type=payload.scan_type)
        return {
            "target": payload.target,
            "success": result.success,
            "emails": result.emails,
            "domains": result.domains,
            "data": result.additional_data,
            "error": result.error,
        }
    except ImportError:
        raise HTTPException(status_code=503, detail="IntelOwl connector not available")
    except Exception as exc:
        logger.exception("IntelOwl analyze error")
        raise HTTPException(status_code=502, detail=f"IntelOwl error: {exc}")


# ---------------------------------------------------------------------------
# Recon-ng
# ---------------------------------------------------------------------------

class ReconNGScanRequest(BaseModel):
    target: str
    workspace: str = "osint_default"


@router.post("/reconng/scan", summary="Run a Recon-ng reconnaissance scan")
async def reconng_scan(
    payload: ReconNGScanRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Runs recon-ng against *target*. Requires recon-ng installed on PATH."""
    try:
        import sys
        sys.path.insert(0, ".")
        from integrations.reconng_connector import ReconNGConnector  # type: ignore
        connector = ReconNGConnector(workspace=payload.workspace)
        result = await connector.search(payload.target)
        return {
            "target": payload.target,
            "success": result.success,
            "emails": result.emails,
            "domains": result.domains,
            "data": result.additional_data,
            "error": result.error,
        }
    except ImportError:
        raise HTTPException(status_code=503, detail="Recon-ng connector not available")
    except Exception as exc:
        logger.exception("Recon-ng scan error")
        raise HTTPException(status_code=502, detail=f"Recon-ng error: {exc}")


# ---------------------------------------------------------------------------
# HIBP
# ---------------------------------------------------------------------------

class HIBPCheckRequest(BaseModel):
    email: str


@router.post("/hibp/check", summary="Check an email against Have I Been Pwned breach database")
async def hibp_check(
    payload: HIBPCheckRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Returns breach and paste data for the given email address."""
    _require_env("HIBP_API_KEY", integration="HIBP")
    try:
        import sys
        sys.path.insert(0, ".")
        from integrations.hibp_connector import HIBPConnector  # type: ignore
        connector = HIBPConnector(api_key=getattr(settings, "HIBP_API_KEY", None))
        result = await connector.gather_intelligence(payload.email)
        return {
            "email": payload.email,
            "success": result.success,
            "breaches": result.additional_data.get("breaches", []),
            "pastes": result.additional_data.get("pastes", []),
            "breach_count": result.additional_data.get("breach_count", 0),
            "risk_level": result.additional_data.get("risk_level", "unknown"),
            "error": result.error,
        }
    except ImportError:
        raise HTTPException(status_code=503, detail="HIBP connector not available")
    except Exception as exc:
        logger.exception("HIBP check error")
        raise HTTPException(status_code=502, detail=f"HIBP check failed: {exc}")


# ---------------------------------------------------------------------------
# SpiderFoot
# ---------------------------------------------------------------------------

class SpiderFootScanRequest(BaseModel):
    target: str
    scan_type: str = "email"


@router.post("/spiderfoot/scan", summary="Trigger a SpiderFoot OSINT scan for a target")
async def spiderfoot_scan(
    payload: SpiderFootScanRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Runs a SpiderFoot scan against *target*. Requires SpiderFoot running locally."""
    try:
        import sys
        sys.path.insert(0, ".")
        from integrations.spiderfoot_connector import SpiderFootConnector  # type: ignore
        sf_url = getattr(settings, "SPIDERFOOT_URL", "http://localhost:5001")
        sf_key = getattr(settings, "SPIDERFOOT_API_KEY", None)
        connector = SpiderFootConnector(api_url=sf_url, api_key=sf_key)
        result = await connector.search(payload.target, search_type=payload.scan_type)
        return {
            "target": payload.target,
            "success": result.success,
            "emails": result.emails,
            "domains": result.domains,
            "data": result.additional_data,
            "error": result.error,
        }
    except ImportError:
        raise HTTPException(status_code=503, detail="SpiderFoot connector not available")
    except Exception as exc:
        logger.exception("SpiderFoot scan error")
        raise HTTPException(status_code=502, detail=f"SpiderFoot scan failed: {exc}")


# ---------------------------------------------------------------------------
# Status overview
# ---------------------------------------------------------------------------

@router.get("/status", summary="Get connection status for all configured integrations")
async def integration_status():
    def _configured(*names: str) -> bool:
        return all(bool(getattr(settings, n, None)) for n in names)

    return {
        "n8n": {
            "configured": _configured("N8N_WEBHOOK_URL"),
            "description": "n8n workflow automation",
        },
        "salesforce": {
            "configured": _configured("SALESFORCE_CLIENT_ID", "SALESFORCE_CLIENT_SECRET", "SALESFORCE_INSTANCE_URL"),
            "description": "Salesforce CRM",
        },
        "hubspot": {
            "configured": _configured("HUBSPOT_ACCESS_TOKEN"),
            "description": "HubSpot CRM",
        },
        "m365": {
            "configured": _configured("M365_TENANT_ID", "M365_CLIENT_ID", "M365_CLIENT_SECRET"),
            "description": "Microsoft 365 People",
        },
        "hibp": {
            "configured": _configured("HIBP_API_KEY"),
            "description": "Have I Been Pwned breach database",
        },
        "spiderfoot": {
            "configured": bool(getattr(settings, "SPIDERFOOT_URL", None)),
            "description": "SpiderFoot OSINT platform",
        },
        "intelowl": {
            "configured": _configured("INTELOWL_API_KEY"),
            "description": "IntelOwl threat intelligence platform",
        },
        "reconng": {
            "configured": bool(getattr(settings, "RECONNG_PATH", None)) or True,
            "description": "Recon-ng (requires recon-ng on PATH)",
        },
    }
