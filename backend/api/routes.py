"""
API Routes Module
Central router configuration for all API endpoints
"""

from fastapi import APIRouter

from .auth_simple import router as auth_router
from .users_simple import router as users_router
from .leads import router as leads_router
from .kpis import router as kpis_router
from .sources import router as sources_router
from .campaigns import router as campaigns_router
from .exports import router as exports_router
from .runs import router as runs_router
from .settings import router as settings_router

# Create main API router
api_router = APIRouter()

# Include sub-routers with prefixes
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    users_router,
    prefix="/users",
    tags=["Users"]
)

api_router.include_router(
    leads_router,
    prefix="/leads",
    tags=["Leads"]
)

api_router.include_router(
    kpis_router,
    prefix="/kpis",
    tags=["KPIs"]
)

api_router.include_router(
    sources_router,
    prefix="/sources",
    tags=["Sources"]
)

api_router.include_router(
    campaigns_router,
    prefix="/campaigns",
    tags=["Campaigns"]
)

api_router.include_router(
    exports_router,
    prefix="/exports",
    tags=["Exports"]
)

api_router.include_router(
    runs_router,
    prefix="/runs",
    tags=["Runs"]
)

api_router.include_router(
    settings_router,
    prefix="/settings",
    tags=["Settings"]
)

# Health check for API
@api_router.get("/", tags=["Root"])
async def api_root():
    """API root endpoint"""
    return {
        "message": "OSINT E-post Etterforsker API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth",
            "users": "/api/users",
            "leads": "/api/leads",
            "kpis": "/api/kpis",
            "sources": "/api/sources",
            "campaigns": "/api/campaigns",
            "exports": "/api/exports",
            "runs": "/api/runs",
            "settings": "/api/settings"
        }
    }

@api_router.get("/version", tags=["Root"])
async def get_api_version():
    """Get API version information"""
    return {
        "api_version": "1.0.0",
        "build_date": "2025-01-22",
        "components": [
            "authentication",
            "user_management",
            "lead_processing",
            "source_management",
            "campaign_management",
            "export_management",
            "run_management",
            "settings_management",
            "osint_crawler",
            "email_validation"
        ]
    }