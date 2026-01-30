"""Custom exceptions for the document forensics API."""

from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError


class DocumentForensicsException(Exception):
    """Base exception for document forensics operations."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class DocumentNotFoundError(DocumentForensicsException):
    """Exception raised when a document is not found."""
    
    def __init__(self, document_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Document {document_id} not found",
            status_code=404,
            details=details
        )


class InvalidDocumentError(DocumentForensicsException):
    """Exception raised when a document is invalid."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Invalid document: {message}",
            status_code=400,
            details=details
        )


class AnalysisError(DocumentForensicsException):
    """Exception raised when analysis fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Analysis failed: {message}",
            status_code=500,
            details=details
        )


class AuthenticationError(DocumentForensicsException):
    """Exception raised for authentication failures."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=401,
            details=details
        )


class AuthorizationError(DocumentForensicsException):
    """Exception raised for authorization failures."""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=403,
            details=details
        )


class BatchProcessingError(DocumentForensicsException):
    """Exception raised for batch processing failures."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Batch processing failed: {message}",
            status_code=500,
            details=details
        )


class WebhookError(DocumentForensicsException):
    """Exception raised for webhook failures."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Webhook error: {message}",
            status_code=500,
            details=details
        )


async def document_forensics_exception_handler(
    request: Request, 
    exc: DocumentForensicsException
) -> JSONResponse:
    """Global exception handler for document forensics exceptions."""
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details,
            "status": "error",
            "path": str(request.url.path),
            "method": request.method
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Global exception handler for HTTP exceptions to ensure consistent error format."""
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status": "error",
            "path": str(request.url.path),
            "method": request.method
        }
    )


async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """Global exception handler for validation errors."""
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "status": "error",
            "path": str(request.url.path),
            "method": request.method
        }
    )