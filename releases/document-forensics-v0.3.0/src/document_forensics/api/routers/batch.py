"""Batch processing router for the document forensics API."""

import logging
from typing import List, Optional, Dict, Any
import time
# UUID removed - using timestamp-based strings

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from ...core.models import BatchStatus, BatchResponse, AnalysisResults
from ...workflow.workflow_manager import WorkflowManager
from ..auth import User, require_read, require_write
from ..exceptions import BatchProcessingError

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Initialize workflow manager
workflow_manager = WorkflowManager()


class BatchProcessRequest(BaseModel):
    """Batch processing request model."""
    document_ids: List[int]
    batch_name: Optional[str] = None
    priority_order: Optional[List[int]] = None
    include_metadata: bool = True
    include_tampering: bool = True
    include_authenticity: bool = True
    reference_samples: Optional[List[str]] = None


class BatchCreateResponse(BaseModel):
    """Batch creation response model."""
    batch_id: str
    message: str
    total_documents: int
    status: str


class BatchResultsResponse(BaseModel):
    """Batch results response model."""
    batch_id: str
    results: Dict[int, AnalysisResults]
    summary: Dict[str, Any]


class BatchListResponse(BaseModel):
    """Batch list response model."""
    batches: List[BatchStatus]
    total: int
    page: int
    page_size: int


@router.post("/process", response_model=BatchCreateResponse)
@limiter.limit("2/minute")
async def create_batch_process(
    request: Request,
    batch_request: BatchProcessRequest,
    current_user: User = Depends(require_write)
):
    """
    Create a new batch processing job.
    
    Rate limited to 2 batch jobs per minute per IP address.
    Requires write permissions.
    """
    try:
        if not batch_request.document_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No document IDs provided"
            )
        
        if len(batch_request.document_ids) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 documents per batch"
            )
        
        # Generate batch ID
        batch_id = str(int(time.time() * 1000000))
        
        # In a real implementation, we would:
        # 1. Validate all document IDs exist in database
        # 2. Get document paths from storage
        # 3. Start batch processing
        
        # Mock document paths (in production, get from database/storage)
        document_paths = [f"/tmp/document_{doc_id}.pdf" for doc_id in batch_request.document_ids]
        
        # Start batch processing (don't await - run in background)
        import asyncio
        asyncio.create_task(
            workflow_manager.process_batch(
                document_paths=document_paths,
                document_ids=batch_request.document_ids,
                batch_id=batch_id,
                priority_order=batch_request.priority_order,
                include_metadata=batch_request.include_metadata,
                include_tampering=batch_request.include_tampering,
                include_authenticity=batch_request.include_authenticity,
                reference_samples=batch_request.reference_samples
            )
        )
        
        logger.info(f"Batch processing started: {batch_id} with {len(batch_request.document_ids)} documents by user {current_user.user_id}")
        
        return BatchCreateResponse(
            batch_id=str(batch_id),
            message="Batch processing started",
            total_documents=len(batch_request.document_ids),
            status="processing"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch processing creation failed: {str(e)}")
        raise BatchProcessingError(str(e))


@router.get("/{batch_id}/status", response_model=BatchResponse)
async def get_batch_status(
    batch_id: str,
    current_user: User = Depends(require_read)
):
    """
    Get batch processing status.
    
    Requires read permissions.
    """
    try:
        batch_status = workflow_manager.get_batch_status(batch_id)
        
        if not batch_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch {batch_id} not found"
            )
        
        return BatchResponse(
            batch_status=batch_status,
            message="Batch status retrieved successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch status {batch_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get batch status: {str(e)}"
        )


@router.get("/{batch_id}/results", response_model=BatchResultsResponse)
async def get_batch_results(
    batch_id: str,
    current_user: User = Depends(require_read)
):
    """
    Get batch processing results.
    
    Requires read permissions.
    """
    try:
        batch_status = workflow_manager.get_batch_status(batch_id)
        
        if not batch_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch {batch_id} not found"
            )
        
        if batch_status.status.value == "processing":
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Batch processing is still in progress"
            )
        
        # In a real implementation, retrieve actual results from storage
        # For now, return mock results
        mock_results = {}
        for i in range(batch_status.total_documents):
            from ...core.models import MetadataAnalysis, RiskLevel
            
            mock_metadata = MetadataAnalysis(
                document_id=i + 1,
                extracted_metadata={"batch_id": batch_id, "mock": f"data_{i}"}
            )
            
            mock_analysis = AnalysisResults(
                document_id=i + 1,
                metadata_analysis=mock_metadata,
                overall_risk_assessment=RiskLevel.LOW,
                confidence_score=0.8
            )
            mock_results[i + 1] = mock_analysis
        
        # Generate summary
        summary = {
            "total_documents": batch_status.total_documents,
            "processed_documents": batch_status.processed_documents,
            "failed_documents": batch_status.failed_documents,
            "success_rate": batch_status.processed_documents / batch_status.total_documents if batch_status.total_documents > 0 else 0,
            "average_confidence": 0.8,  # Mock value
            "risk_distribution": {
                "low": batch_status.processed_documents,
                "medium": 0,
                "high": 0,
                "critical": 0
            }
        }
        
        logger.info(f"Batch results retrieved for {batch_id} by user {current_user.user_id}")
        
        return BatchResultsResponse(
            batch_id=batch_id,
            results=mock_results,
            summary=summary
        )
    
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid batch ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch results {batch_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get batch results: {str(e)}"
        )


@router.get("/", response_model=BatchListResponse)
async def list_batches(
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None,
    current_user: User = Depends(require_read)
):
    """
    List batch processing jobs with pagination and filtering.
    
    Requires read permissions.
    """
    try:
        # In a real implementation, this would query the database
        # For now, we'll return mock data from workflow manager
        
        all_batches = list(workflow_manager.batch_progress.values())
        
        # Apply status filter
        if status_filter:
            all_batches = [
                batch for batch in all_batches
                if batch.status.value == status_filter
            ]
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_batches = all_batches[start_idx:end_idx]
        
        logger.info(f"Listed {len(paginated_batches)} batches for user {current_user.user_id}")
        
        return BatchListResponse(
            batches=paginated_batches,
            total=len(all_batches),
            page=page,
            page_size=page_size
        )
    
    except Exception as e:
        logger.error(f"Error listing batches: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list batches: {str(e)}"
        )


@router.delete("/{batch_id}")
async def cancel_batch(
    batch_id: str,
    current_user: User = Depends(require_write)
):
    """
    Cancel a batch processing job.
    
    Requires write permissions.
    """
    try:
        batch_status = workflow_manager.get_batch_status(batch_id)
        
        if not batch_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch {batch_id} not found"
            )
        
        if batch_status.status.value != "processing":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel batch in {batch_status.status.value} status"
            )
        
        # In a real implementation, this would cancel the running batch
        # For now, we'll just update the status
        batch_status.status = "cancelled"
        
        logger.info(f"Batch {batch_id} cancelled by user {current_user.user_id}")
        
        return {"message": f"Batch {batch_id} cancelled successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling batch {batch_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel batch: {str(e)}"
        )


@router.get("/{batch_id}/report")
async def download_batch_report(
    batch_id: str,
    format: str = "json",
    current_user: User = Depends(require_read)
):
    """
    Download comprehensive batch report.
    
    Requires read permissions.
    """
    try:
        batch_status = workflow_manager.get_batch_status(batch_id)
        
        if not batch_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch {batch_id} not found"
            )
        
        if batch_status.status.value == "processing":
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Batch processing is still in progress"
            )
        
        # In a real implementation, this would generate and return the actual report
        # For now, return a mock response
        
        if format.lower() not in ["json", "pdf", "xml"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supported formats: json, pdf, xml"
            )
        
        logger.info(f"Batch report requested for {batch_id} in {format} format by user {current_user.user_id}")
        
        return {
            "message": f"Batch report for {batch_id} in {format} format",
            "download_url": f"/api/v1/batch/{batch_id}/report/download?format={format}",
            "expires_at": "2024-01-01T00:00:00Z"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating batch report {batch_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate batch report: {str(e)}"
        )