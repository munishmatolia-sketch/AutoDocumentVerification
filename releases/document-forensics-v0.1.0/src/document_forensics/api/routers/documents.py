"""Documents router for the document forensics API."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from ...core.models import (
    Document, DocumentResponse, UploadMetadata, ValidationResult, ErrorResponse
)
from ...upload.manager import UploadManager
from ..auth import User, require_read, require_write
from ..exceptions import DocumentNotFoundError, InvalidDocumentError

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Initialize upload manager
upload_manager = UploadManager()


class DocumentUploadResponse(BaseModel):
    """Document upload response model."""
    success: bool
    document_id: str
    document: Optional[Document] = None
    warnings: List[str] = []
    errors: List[str] = []


class DocumentListResponse(BaseModel):
    """Document list response model."""
    documents: List[Document]
    total: int
    page: int
    page_size: int


@router.post("/upload", response_model=DocumentUploadResponse)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    priority: int = Form(5),
    encrypt: bool = Form(True),
    current_user: User = Depends(require_write)
):
    """
    Upload a document for forensic analysis.
    
    Rate limited to 10 uploads per minute per IP address.
    Requires write permissions.
    """
    try:
        # Validate file
        if not file.filename:
            raise InvalidDocumentError("No filename provided")
        
        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # Create upload metadata
        upload_metadata = UploadMetadata(
            description=description,
            tags=tag_list,
            priority=priority,
            user_id=current_user.user_id
        )
        
        # Read file content
        file_content = await file.read()
        
        # Upload document
        result = await upload_manager.upload_document(
            file_data=file_content,
            filename=file.filename,
            upload_metadata=upload_metadata,
            encrypt=encrypt
        )
        
        if result["success"]:
            logger.info(f"Document uploaded successfully: {result['document_id']}")
            return DocumentUploadResponse(
                success=True,
                document_id=result["document_id"],
                document=result.get("document"),
                warnings=result.get("warnings", [])
            )
        else:
            logger.warning(f"Document upload failed: {result.get('errors', [])}")
            return DocumentUploadResponse(
                success=False,
                document_id=result["document_id"],
                errors=result.get("errors", []),
                warnings=result.get("warnings", [])
            )
    
    except InvalidDocumentError:
        raise
    except Exception as e:
        logger.error(f"Document upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/validate", response_model=ValidationResult)
@limiter.limit("20/minute")
async def validate_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_read)
):
    """
    Validate a document without uploading it.
    
    Rate limited to 20 validations per minute per IP address.
    Requires read permissions.
    """
    try:
        if not file.filename:
            raise InvalidDocumentError("No filename provided")
        
        # Create temporary file for validation
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            
            try:
                # Validate using upload manager
                validation_result = upload_manager.validate_format(
                    temp_file.name, 
                    file.filename
                )
                
                logger.info(f"Document validation completed for {file.filename}")
                return validation_result
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file.name)
    
    except InvalidDocumentError:
        raise
    except Exception as e:
        logger.error(f"Document validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(require_read)
):
    """
    Get document information by ID.
    
    Requires read permissions.
    """
    try:
        # Validate document ID format (should be numeric or UUID)
        # First check for obviously invalid characters that should return 400
        invalid_chars = set(document_id) & set('?;:<>|*"\\/ \t\n\r')
        if invalid_chars:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document ID format: contains invalid characters"
            )
        
        # Check for empty or whitespace-only IDs
        if not document_id or not document_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document ID cannot be empty"
            )
        
        try:
            # Try to parse as integer first
            doc_id = int(document_id)
            if doc_id <= 0:
                raise ValueError("Document ID must be positive")
        except ValueError:
            # Then try UUID
            try:
                UUID(document_id)
            except ValueError:
                # If not UUID either, check if it's a reasonable alphanumeric string
                if not document_id.replace('-', '').replace('_', '').isalnum():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid document ID format: {document_id}"
                    )
        
        # In a real implementation, this would query the database
        # For now, we'll return a mock response
        
        # Mock document retrieval
        document = Document(
            id=1,
            filename=f"document_{document_id}.pdf",
            file_type="pdf",
            size=1024000,
            hash="a" * 64,
            processing_status="completed"
        )
        
        logger.info(f"Document {document_id} retrieved by user {current_user.user_id}")
        return DocumentResponse(
            document=document,
            message="Document retrieved successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document {document_id}: {str(e)}")
        raise DocumentNotFoundError(document_id)


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None,
    current_user: User = Depends(require_read)
):
    """
    List documents with pagination and filtering.
    
    Requires read permissions.
    """
    try:
        # In a real implementation, this would query the database
        # For now, we'll return mock data
        
        mock_documents = [
            Document(
                id=i,
                filename=f"document_{i}.pdf",
                file_type="pdf",
                size=1024000 + i * 1000,
                hash="a" * 64,
                processing_status="completed"
            )
            for i in range(1, 11)
        ]
        
        # Apply status filter if provided
        if status_filter:
            mock_documents = [
                doc for doc in mock_documents 
                if doc.processing_status == status_filter
            ]
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_docs = mock_documents[start_idx:end_idx]
        
        logger.info(f"Listed {len(paginated_docs)} documents for user {current_user.user_id}")
        
        return DocumentListResponse(
            documents=paginated_docs,
            total=len(mock_documents),
            page=page,
            page_size=page_size
        )
    
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(require_write)
):
    """
    Delete a document.
    
    Requires write permissions.
    """
    try:
        # Convert string ID to UUID for storage operations
        doc_uuid = UUID(document_id)
        
        # Delete from storage
        deleted = await upload_manager.delete_document(doc_uuid)
        
        if deleted:
            logger.info(f"Document {document_id} deleted by user {current_user.user_id}")
            return {"message": f"Document {document_id} deleted successfully"}
        else:
            raise DocumentNotFoundError(document_id)
    
    except ValueError:
        raise InvalidDocumentError("Invalid document ID format")
    except DocumentNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


@router.get("/{document_id}/integrity")
async def verify_document_integrity(
    document_id: str,
    expected_hash: Optional[str] = None,
    current_user: User = Depends(require_read)
):
    """
    Verify document integrity using hash comparison.
    
    Requires read permissions.
    """
    try:
        doc_uuid = UUID(document_id)
        
        if not expected_hash:
            # If no expected hash provided, just return current hash
            # In a real implementation, this would get the hash from database
            return {
                "document_id": document_id,
                "integrity_verified": True,
                "message": "No expected hash provided for comparison"
            }
        
        # Verify integrity
        is_valid = await upload_manager.verify_document_integrity(
            doc_uuid, expected_hash
        )
        
        logger.info(f"Integrity verification for document {document_id}: {is_valid}")
        
        return {
            "document_id": document_id,
            "integrity_verified": is_valid,
            "expected_hash": expected_hash,
            "message": "Integrity verified" if is_valid else "Integrity check failed"
        }
    
    except ValueError:
        raise InvalidDocumentError("Invalid document ID format")
    except Exception as e:
        logger.error(f"Error verifying integrity for document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Integrity verification failed: {str(e)}"
        )