"""Analysis router for the document forensics API."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from ...core.models import AnalysisResults, AnalysisResponse, ErrorResponse
from ...workflow.workflow_manager import WorkflowManager
from ..auth import User, require_read, require_write
from ..exceptions import DocumentNotFoundError, AnalysisError

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Initialize workflow manager
workflow_manager = WorkflowManager()


class AnalysisRequest(BaseModel):
    """Analysis request model."""
    document_id: int
    include_metadata: bool = True
    include_tampering: bool = True
    include_authenticity: bool = True
    reference_samples: Optional[List[str]] = None
    priority: int = 5


class AnalysisStatusResponse(BaseModel):
    """Analysis status response model."""
    document_id: int
    status: str
    progress_percentage: float
    current_step: str
    start_time: str
    errors: List[dict] = []


class AnalysisListResponse(BaseModel):
    """Analysis list response model."""
    analyses: List[AnalysisResults]
    total: int
    page: int
    page_size: int


@router.post("/analyze", response_model=AnalysisResponse)
@limiter.limit("5/minute")
async def analyze_document(
    request: Request,
    analysis_request: AnalysisRequest,
    current_user: User = Depends(require_write)
):
    """
    Start forensic analysis of a document.
    
    Rate limited to 5 analyses per minute per IP address.
    Requires write permissions.
    """
    try:
        # In a real implementation, we would:
        # 1. Validate document exists in database
        # 2. Get document path from storage
        # 3. Start analysis
        
        # Mock document path (in production, get from database/storage)
        document_path = f"/tmp/document_{analysis_request.document_id}.pdf"
        
        # Start analysis
        analysis_results = await workflow_manager.analyze_document(
            document_path=document_path,
            document_id=analysis_request.document_id,
            priority=analysis_request.priority,
            include_metadata=analysis_request.include_metadata,
            include_tampering=analysis_request.include_tampering,
            include_authenticity=analysis_request.include_authenticity,
            reference_samples=analysis_request.reference_samples
        )
        
        logger.info(f"Analysis completed for document {analysis_request.document_id} by user {current_user.user_id}")
        
        return AnalysisResponse(
            results=analysis_results,
            message="Analysis completed successfully"
        )
    
    except FileNotFoundError:
        raise DocumentNotFoundError(str(analysis_request.document_id))
    except Exception as e:
        logger.error(f"Analysis failed for document {analysis_request.document_id}: {str(e)}")
        raise AnalysisError(str(e))


@router.get("/{document_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    document_id: str,
    current_user: User = Depends(require_read)
):
    """
    Get analysis status for a document.
    
    Requires read permissions.
    """
    try:
        # Validate document ID format
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
            doc_id = int(document_id)
            if doc_id <= 0:
                raise ValueError("Document ID must be positive")
        except ValueError:
            # If not integer and has invalid chars, it's definitely invalid
            if not document_id.replace('-', '').replace('_', '').isalnum():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid document ID format: {document_id}"
                )
        
        progress = workflow_manager.get_document_progress(doc_id)
        
        if not progress:
            raise DocumentNotFoundError(document_id)
        
        return AnalysisStatusResponse(
            document_id=doc_id,
            status=progress["status"].value if hasattr(progress["status"], "value") else str(progress["status"]),
            progress_percentage=progress.get("progress_percentage", 0.0),
            current_step=progress.get("current_step", "unknown"),
            start_time=progress.get("start_time", "").isoformat() if progress.get("start_time") else "",
            errors=progress.get("errors", [])
        )
    
    except HTTPException:
        raise
    except DocumentNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis status for document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analysis status: {str(e)}"
        )


@router.get("/{document_id}/results", response_model=AnalysisResponse)
async def get_analysis_results(
    document_id: int,
    current_user: User = Depends(require_read)
):
    """
    Get analysis results for a document.
    
    Requires read permissions.
    """
    try:
        # In a real implementation, this would query the database for stored results
        # For now, we'll return a mock response or re-run analysis
        
        # Check if analysis is in progress
        progress = workflow_manager.get_document_progress(document_id)
        
        if progress and progress.get("status") == "processing":
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Analysis is still in progress"
            )
        
        # Mock analysis results (in production, retrieve from database)
        from ...core.models import MetadataAnalysis, RiskLevel
        
        mock_metadata = MetadataAnalysis(
            document_id=document_id,
            extracted_metadata={"mock": "data"}
        )
        
        mock_results = AnalysisResults(
            document_id=document_id,
            metadata_analysis=mock_metadata,
            overall_risk_assessment=RiskLevel.LOW,
            confidence_score=0.85
        )
        
        logger.info(f"Analysis results retrieved for document {document_id} by user {current_user.user_id}")
        
        return AnalysisResponse(
            results=mock_results,
            message="Analysis results retrieved successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis results for document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analysis results: {str(e)}"
        )


@router.get("/", response_model=AnalysisListResponse)
async def list_analyses(
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None,
    risk_filter: Optional[str] = None,
    current_user: User = Depends(require_read)
):
    """
    List analysis results with pagination and filtering.
    
    Requires read permissions.
    """
    try:
        # In a real implementation, this would query the database
        # For now, we'll return mock data
        
        from ...core.models import MetadataAnalysis, RiskLevel
        
        mock_analyses = []
        for i in range(1, 21):
            mock_metadata = MetadataAnalysis(
                document_id=i,
                extracted_metadata={"mock": f"data_{i}"}
            )
            
            mock_analysis = AnalysisResults(
                document_id=i,
                metadata_analysis=mock_metadata,
                overall_risk_assessment=RiskLevel.LOW if i % 2 == 0 else RiskLevel.MEDIUM,
                confidence_score=0.8 + (i % 10) * 0.02
            )
            mock_analyses.append(mock_analysis)
        
        # Apply filters
        if risk_filter:
            mock_analyses = [
                analysis for analysis in mock_analyses
                if analysis.overall_risk_assessment.value == risk_filter
            ]
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_analyses = mock_analyses[start_idx:end_idx]
        
        logger.info(f"Listed {len(paginated_analyses)} analyses for user {current_user.user_id}")
        
        return AnalysisListResponse(
            analyses=paginated_analyses,
            total=len(mock_analyses),
            page=page,
            page_size=page_size
        )
    
    except Exception as e:
        logger.error(f"Error listing analyses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list analyses: {str(e)}"
        )


@router.delete("/{document_id}/results")
async def delete_analysis_results(
    document_id: int,
    current_user: User = Depends(require_write)
):
    """
    Delete analysis results for a document.
    
    Requires write permissions.
    """
    try:
        # In a real implementation, this would delete from database
        # For now, we'll just return success
        
        logger.info(f"Analysis results deleted for document {document_id} by user {current_user.user_id}")
        
        return {"message": f"Analysis results for document {document_id} deleted successfully"}
    
    except Exception as e:
        logger.error(f"Error deleting analysis results for document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete analysis results: {str(e)}"
        )


@router.post("/{document_id}/reanalyze", response_model=AnalysisResponse)
@limiter.limit("3/minute")
async def reanalyze_document(
    request: Request,
    document_id: int,
    analysis_request: Optional[AnalysisRequest] = None,
    current_user: User = Depends(require_write)
):
    """
    Re-run analysis on a document with updated parameters.
    
    Rate limited to 3 re-analyses per minute per IP address.
    Requires write permissions.
    """
    try:
        # Use provided request or default parameters
        if not analysis_request:
            analysis_request = AnalysisRequest(document_id=document_id)
        else:
            analysis_request.document_id = document_id  # Ensure consistency
        
        # Re-run analysis
        analysis_results = await analyze_document(request, analysis_request, current_user)
        
        logger.info(f"Document {document_id} re-analyzed by user {current_user.user_id}")
        
        return analysis_results
    
    except Exception as e:
        logger.error(f"Re-analysis failed for document {document_id}: {str(e)}")
        raise AnalysisError(f"Re-analysis failed: {str(e)}")