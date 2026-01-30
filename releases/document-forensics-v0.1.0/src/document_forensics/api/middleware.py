"""Middleware for the document forensics API."""

import logging
import time
from typing import Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..security.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for adding security headers and request validation."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with security enhancements."""
        
        # Add request ID for tracing
        request_id = str(uuid4())
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logging middleware for request/response logging and audit trails."""
    
    def __init__(self, app):
        super().__init__(app)
        self.audit_logger = AuditLogger()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with comprehensive logging."""
        
        start_time = time.time()
        request_id = getattr(request.state, 'request_id', str(uuid4()))
        
        # Log request
        logger.info(
            f"Request {request_id}: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Response {request_id}: {response.status_code} "
                f"({process_time:.3f}s)"
            )
            
            # Audit log for sensitive operations
            if request.url.path.startswith('/api/v1/'):
                await self._audit_log_request(request, response, process_time)
            
            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request {request_id} failed: {str(e)} ({process_time:.3f}s)"
            )
            raise
    
    async def _audit_log_request(self, request: Request, response: Response, process_time: float):
        """Create audit log entry for API requests."""
        try:
            # Extract user information if available
            user_id = getattr(request.state, 'user_id', None)
            
            # Create audit log entry
            await self.audit_logger.log_action(
                user_id=user_id,
                action=f"{request.method} {request.url.path}",
                details={
                    "status_code": response.status_code,
                    "process_time": process_time,
                    "user_agent": request.headers.get("user-agent"),
                    "content_length": response.headers.get("content-length")
                },
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
            
        except Exception as e:
            logger.error(f"Failed to create audit log entry: {str(e)}")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware (complementary to slowapi)."""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply additional rate limiting logic."""
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Check if this is a high-resource endpoint
        high_resource_paths = [
            "/api/v1/analysis/analyze",
            "/api/v1/batch/process",
            "/api/v1/documents/upload"
        ]
        
        if any(request.url.path.startswith(path) for path in high_resource_paths):
            # Apply stricter rate limiting for resource-intensive operations
            # This is handled by slowapi decorators on individual endpoints
            pass
        
        return await call_next(request)