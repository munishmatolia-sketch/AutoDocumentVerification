"""Main FastAPI application for document forensics API."""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from ..core.config import settings
from .routers import documents, analysis, batch, reports, auth, webhooks
from .middleware import SecurityMiddleware, LoggingMiddleware
from .exceptions import (
    DocumentForensicsException, 
    document_forensics_exception_handler,
    http_exception_handler,
    validation_exception_handler
)

logger = logging.getLogger(__name__)

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Document Forensics API")
    
    # Initialize any required services here
    # For example: database connections, ML models, etc.
    
    yield
    
    # Shutdown
    logger.info("Shutting down Document Forensics API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Document Forensics & Verification API",
        description="AI-Powered Document Forensics & Verification System",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # Add rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Add custom exception handlers (order matters - most specific first)
    app.add_exception_handler(DocumentForensicsException, document_forensics_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Add middleware
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(LoggingMiddleware)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
    app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
    app.include_router(batch.router, prefix="/api/v1/batch", tags=["Batch Processing"])
    app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
    app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "document-forensics-api"}
    
    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "service": "Document Forensics & Verification API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health"
        }
    
    return app


# Create the application instance
app = create_app()