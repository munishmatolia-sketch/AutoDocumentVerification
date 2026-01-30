"""Analysis router for the document forensics API."""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from ...core.models import AnalysisResults, AnalysisResponse, ErrorResponse
from ...workflow.workflow_manager import WorkflowManager
from ...database.connection import get_db
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
    current_user: Optional[User] = None
):
    """
    Start forensic analysis of a document.
    
    Rate limited to 5 analyses per minute per IP address.
    Authentication is optional for demo purposes.
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
        
        user_id = current_user.user_id if current_user else "anonymous"
        logger.info(f"Analysis completed for document {analysis_request.document_id} by user {user_id}")
        
        return AnalysisResponse(
            results=analysis_results,
            message="Analysis completed successfully"
        )
    
    except FileNotFoundError:
        raise DocumentNotFoundError(str(analysis_request.document_id))
    except Exception as e:
        logger.error(f"Analysis failed for document {analysis_request.document_id}: {str(e)}")
        raise AnalysisError(str(e))


class StartAnalysisRequest(BaseModel):
    """Start analysis request model."""
    document_id: str


@router.post("/start")
@limiter.limit("10/minute")
async def start_analysis(
    request: Request,
    document_id: str = Body(..., embed=True),
    current_user: Optional[User] = None,
    db: Session = Depends(get_db)
):
    """
    Start analysis for a document (with full database integration).
    
    Rate limited to 10 analyses per minute per IP address.
    Authentication is optional for demo purposes.
    
    Request body:
    ```json
    {
        "document_id": "123"
    }
    ```
    """
    try:
        from ...database.models import Document as DBDocument, AnalysisProgress, AnalysisResult
        from sqlalchemy import select
        
        # Convert document_id to integer
        try:
            doc_id = int(document_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document ID format: {document_id}"
            )
        
        # Get document from database
        document = db.query(DBDocument).filter(DBDocument.id == doc_id).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        # Create progress tracking
        progress = AnalysisProgress(
            document_id=doc_id,
            status="processing",
            progress_percentage=0.0,
            current_step="Starting analysis",
            start_time=datetime.now()
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)
        
        logger.info(f"Starting analysis for document {document_id} at path: {document.file_path}")
        
        # Start analysis using workflow manager
        try:
            # Update progress
            progress.current_step = "Running forensic analysis"
            progress.progress_percentage = 25.0
            db.commit()
            
            # Execute analysis
            analysis_results = await workflow_manager.analyze_document(
                document_path=document.file_path,
                document_id=str(document.id),
                priority=5,
                include_metadata=True,
                include_tampering=True,
                include_authenticity=True
            )
            
            # Update progress
            progress.status = "completed"
            progress.progress_percentage = 100.0
            progress.current_step = "Analysis complete"
            progress.end_time = datetime.now()
            db.commit()
            
            # Save results to database
            result_record = AnalysisResult(
                document_id=doc_id,
                analysis_type="full",
                results=analysis_results.model_dump() if hasattr(analysis_results, 'model_dump') else {},
                confidence_score=analysis_results.confidence_score if hasattr(analysis_results, 'confidence_score') else None,
                risk_level=analysis_results.overall_risk_assessment.value if hasattr(analysis_results, 'overall_risk_assessment') else None,
                metadata_analysis=analysis_results.metadata_analysis.model_dump() if hasattr(analysis_results, 'metadata_analysis') and analysis_results.metadata_analysis else None,
                tampering_analysis=analysis_results.tampering_analysis.model_dump() if hasattr(analysis_results, 'tampering_analysis') and analysis_results.tampering_analysis else None,
                authenticity_analysis=analysis_results.authenticity_analysis.model_dump() if hasattr(analysis_results, 'authenticity_analysis') and analysis_results.authenticity_analysis else None
            )
            db.add(result_record)
            
            # Update document status
            document.processing_status = "completed"
            db.commit()
            
            logger.info(f"Analysis completed successfully for document {document_id}")
            
            return {
                "status": "success",
                "message": "Analysis completed successfully",
                "document_id": str(document_id),
                "results": {
                    "confidence_score": analysis_results.confidence_score if hasattr(analysis_results, 'confidence_score') else None,
                    "risk_level": analysis_results.overall_risk_assessment.value if hasattr(analysis_results, 'overall_risk_assessment') else None
                }
            }
            
        except Exception as analysis_error:
            # Update progress with error
            progress.status = "failed"
            progress.current_step = "Analysis failed"
            progress.end_time = datetime.now()
            progress.errors = [{"error": str(analysis_error), "timestamp": datetime.now().isoformat()}]
            
            # Update document status
            document.processing_status = "failed"
            db.commit()
            
            logger.error(f"Analysis failed for document {document_id}: {str(analysis_error)}")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Analysis failed: {str(analysis_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start analysis for document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start analysis: {str(e)}"
        )


@router.get("/{document_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    document_id: str,
    current_user: Optional[User] = None,
    db: Session = Depends(get_db)
):
    """
    Get analysis status for a document from database.
    
    Authentication is optional for demo purposes.
    """
    try:
        from ...database.models import AnalysisProgress
        
        # Convert document_id to integer
        try:
            doc_id = int(document_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document ID format: {document_id}"
            )
        
        # Get latest progress from database
        progress = db.query(AnalysisProgress).filter(
            AnalysisProgress.document_id == doc_id
        ).order_by(AnalysisProgress.created_at.desc()).first()
        
        if not progress:
            # No progress found - document might not have started analysis yet
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No analysis found for document {document_id}"
            )
        
        return AnalysisStatusResponse(
            document_id=0,  # Not used anymore
            status=progress.status,
            progress_percentage=progress.progress_percentage,
            current_step=progress.current_step or "",
            start_time=progress.start_time.isoformat() if progress.start_time else "",
            errors=progress.errors or []
        )
        
    except HTTPException:
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


# Forgery Detection Endpoints
class ForgeryDetectionRequest(BaseModel):
    """Forgery detection request model."""
    document_id: int


@router.post("/detect-forgery", response_model=dict, tags=["forgery"])
@limiter.limit("20/minute")
async def detect_forgery(
    request: Request,
    forgery_request: ForgeryDetectionRequest,
    current_user: User = Depends(require_read)
):
    """
    Detect forgery in an uploaded document.
    
    Performs format-specific forgery detection including:
    - **Word**: Revision history, style inconsistencies, hidden text, track changes
    - **Excel**: Formula tampering, hidden content, macros, data validation
    - **Text**: Encoding manipulation, invisible characters, homoglyphs
    - **Images**: Clone detection, noise analysis, lighting inconsistencies
    - **PDF**: Signature verification, incremental updates, object manipulation
    
    Returns detailed forgery indicators with confidence scores and severity levels.
    """
    try:
        logger.info(f"Forgery detection requested for document {forgery_request.document_id} by user {current_user.username}")
        
        # Get document path from workflow manager
        document = await workflow_manager.get_document(forgery_request.document_id)
        if not document:
            raise DocumentNotFoundError(f"Document {forgery_request.document_id} not found")
        
        # Run forgery detection
        from ...analysis.forgery_detector import ForgeryDetector
        detector = ForgeryDetector()
        
        forgery_analysis = await detector.detect_forgery(
            document.file_path,
            forgery_request.document_id
        )
        
        # Convert to dict for response
        result = {
            "document_id": forgery_analysis.document_id,
            "document_type": forgery_analysis.document_type,
            "overall_risk": forgery_analysis.overall_risk,
            "confidence_score": forgery_analysis.confidence_score,
            "indicators": [
                {
                    "type": ind.type,
                    "description": ind.description,
                    "confidence": ind.confidence,
                    "severity": ind.severity,
                    "location": ind.location,
                    "evidence": ind.evidence,
                    "detection_method": ind.detection_method
                }
                for ind in forgery_analysis.indicators
            ],
            "detection_methods_used": forgery_analysis.detection_methods_used,
            "timestamp": forgery_analysis.timestamp.isoformat()
        }
        
        logger.info(f"Forgery detection completed for document {forgery_request.document_id}: {forgery_analysis.overall_risk} risk")
        
        return {
            "status": "success",
            "message": f"Forgery detection completed. Risk level: {forgery_analysis.overall_risk}",
            "data": result
        }
        
    except DocumentNotFoundError as e:
        logger.error(f"Document not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in forgery detection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forgery detection failed: {str(e)}"
        )


@router.get("/forgery-report/{document_id}", tags=["forgery"])
@limiter.limit("10/minute")
async def get_forgery_report(
    request: Request,
    document_id: int,
    current_user: User = Depends(require_read)
):
    """
    Get detailed forgery analysis report for a document.
    
    Returns comprehensive forgery analysis including all indicators,
    evidence, and recommendations.
    """
    try:
        logger.info(f"Forgery report requested for document {document_id} by user {current_user.username}")
        
        # Get document and forgery analysis
        document = await workflow_manager.get_document(document_id)
        if not document:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        
        # Get stored forgery analysis or run new detection
        forgery_analysis = await workflow_manager.get_forgery_analysis(document_id)
        
        if not forgery_analysis:
            # Run new detection
            from ...analysis.forgery_detector import ForgeryDetector
            detector = ForgeryDetector()
            forgery_analysis = await detector.detect_forgery(
                document.file_path,
                document_id
            )
        
        # Generate comprehensive report
        report = {
            "document_id": document_id,
            "document_name": document.filename,
            "document_type": forgery_analysis.document_type,
            "analysis_timestamp": forgery_analysis.timestamp.isoformat(),
            "overall_assessment": {
                "risk_level": forgery_analysis.overall_risk,
                "confidence_score": forgery_analysis.confidence_score,
                "total_indicators": len(forgery_analysis.indicators)
            },
            "indicators_by_severity": {
                "critical": [ind for ind in forgery_analysis.indicators if ind.severity == "CRITICAL"],
                "high": [ind for ind in forgery_analysis.indicators if ind.severity == "HIGH"],
                "medium": [ind for ind in forgery_analysis.indicators if ind.severity == "MEDIUM"],
                "low": [ind for ind in forgery_analysis.indicators if ind.severity == "LOW"]
            },
            "detection_methods": forgery_analysis.detection_methods_used,
            "recommendations": _generate_recommendations(forgery_analysis)
        }
        
        return {
            "status": "success",
            "message": "Forgery report generated successfully",
            "report": report
        }
        
    except DocumentNotFoundError as e:
        logger.error(f"Document not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating forgery report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )


def _generate_recommendations(forgery_analysis) -> List[str]:
    """Generate recommendations based on forgery analysis."""
    recommendations = []
    
    if forgery_analysis.overall_risk in ["HIGH", "CRITICAL"]:
        recommendations.append("Document shows significant signs of forgery. Further investigation recommended.")
        recommendations.append("Consider requesting original document from source.")
        recommendations.append("Consult with forensic document examiner for expert analysis.")
    
    if any(ind.type == "HIDDEN_TEXT" for ind in forgery_analysis.indicators):
        recommendations.append("Hidden text detected. Review document carefully for concealed information.")
    
    if any(ind.type == "FORMULA_TAMPERING" for ind in forgery_analysis.indicators):
        recommendations.append("Formula tampering detected in spreadsheet. Verify all calculations manually.")
    
    if any(ind.type == "SIGNATURE_BROKEN" for ind in forgery_analysis.indicators):
        recommendations.append("Digital signature issues detected. Verify document authenticity with signer.")
    
    if forgery_analysis.overall_risk == "LOW":
        recommendations.append("No significant forgery indicators detected. Document appears authentic.")
    
    return recommendations
