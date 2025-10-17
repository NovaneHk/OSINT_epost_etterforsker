"""
OSINT E-post Etterforsker - FastAPI Backend
Main application entry point with middleware, routing, and startup configuration
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from backend.core.config import get_settings
from backend.core.database import create_tables, close_db_connections
from backend.core.logging import setup_logging
from backend.api.routes import api_router
from backend.core.error_handlers import setup_exception_handlers
from backend.middleware.rate_limiter import RateLimiterMiddleware
from backend.middleware.request_logger import RequestLoggerMiddleware

settings = get_settings()
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting OSINT E-post Etterforsker Backend")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Initialize database
    if settings.CREATE_TABLES_ON_STARTUP:
        logger.info("📊 Creating database tables...")
        await create_tables()
        logger.info("✅ Database tables created")

    logger.info("✅ Backend startup complete")

    yield

    # Shutdown
    logger.info("🔄 Shutting down backend...")
    await close_db_connections()
    logger.info("✅ Backend shutdown complete")


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
    )

    # Security middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count", "X-Page-Count"]
    )

    # Session middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=settings.SESSION_MAX_AGE,
        same_site="lax",
        https_only=settings.ENVIRONMENT == "production"
    )

    # Custom middleware
    app.add_middleware(RateLimiterMiddleware)
    app.add_middleware(RequestLoggerMiddleware)

    # Setup error handlers
    setup_exception_handlers(app)

    # Include API routes
    app.include_router(api_router, prefix="/api")

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Simple health check endpoint"""
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT
        }

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information"""
        return {
            "message": f"Welcome to {settings.PROJECT_NAME} API",
            "version": settings.VERSION,
            "docs_url": "/api/docs" if settings.DEBUG else "Documentation not available in production",
            "health_check": "/health"
        }


    # Serve static files in development
    if settings.DEBUG and settings.STATIC_FILES_DIR:
        app.mount("/static", StaticFiles(directory=settings.STATIC_FILES_DIR), name="static")

    return app


# Create the FastAPI application
app = create_application()


if __name__ == "__main__":
    """Run the application with uvicorn"""
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
        access_log=True,
        use_colors=True,
        loop="asyncio"
    )
