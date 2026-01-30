"""Reports router for the document forensics API."""

import logging
from typing import Optional, List
# UUID removed - using integer IDs

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from ...core.models import ReportFormat, AnalysisResults, AuditAction
from ...reporting.report_manager import ReportManager
from ..auth import User, require_read, require_write
from ..exceptions import DocumentNotFoundError

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Initialize report manager
report_manager = ReportManager()


class ReportRequest(BaseModel):
    """Report generation request model."""
    document_id: int
    format: ReportFormat = ReportFormat.PDF
    include_visual_evidence: bool = True
    include_technical_details: bool = True


class ReportResponse(BaseModel):
    """Report generation response model."""
    document_id: int
    format: str
    size_bytes: int
    generated_at: str
    download_url: str


class ReportListResponse(BaseModel):
    """Report list response model."""
    reports: List[dict]
    total: int
    page: int
    page_size: int


@router.post("/generate", response_model=ReportResponse)
@limiter.limit("10/minute")
async def generate_report(
    request: Request,
    report_request: ReportRequest,
    current_user: User = Depends(require_read)
):
    """
    Generate a forensic analysis report.
    
    Rate limited to 10 reports per minute per IP address.
    Requires read permissions.
    """
    try:
        # In a real implementation, we would:
        # 1. Validate document exists and has analysis results
        # 2. Retrieve analysis results from database
        # 3. Generate report using report manager
        
        # Mock analysis results (in production, retrieve from database)
        from ...core.models import MetadataAnalysis, RiskLevel
        from datetime import datetime
        
        mock_metadata = MetadataAnalysis(
            document_id=request.document_id,
            extracted_metadata={"mock": "data for report"}
        )
        
        mock_analysis_results = AnalysisResults(
            document_id=report_request.document_id,
            metadata_analysis=mock_metadata,
            overall_risk_assessment=RiskLevel.LOW,
            confidence_score=0.85,
            timestamp=datetime.utcnow()
        )
        
        # Generate report
        report_content = await report_manager.generate_report(
            analysis_results=mock_analysis_results,
            report_format=report_request.format,
            include_visual_evidence=report_request.include_visual_evidence,
            include_technical_details=report_request.include_technical_details
        )
        
        # In a real implementation, we would store the report and return a download URL
        # For now, we'll return metadata about the generated report
        
        logger.info(f"Report generated for document {report_request.document_id} in {report_request.format.value} format by user {current_user.user_id}")
        
        return ReportResponse(
            document_id=report_request.document_id,
            format=report_request.format.value,
            size_bytes=len(report_content),
            generated_at=datetime.utcnow().isoformat(),
            download_url=f"/api/v1/reports/{report_request.document_id}/download?format={report_request.format.value}"
        )
    
    except Exception as e:
        logger.error(f"Report generation failed for document {report_request.document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )


@router.get("/{document_id}/download")
@limiter.limit("20/minute")
async def download_report(
    request: Request,
    document_id: str,
    format: str = "pdf",
    current_user: User = Depends(require_read)
):
    """
    Download a generated report.
    
    Rate limited to 20 downloads per minute per IP address.
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
        
        # Validate format
        try:
            report_format = ReportFormat(format.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {format}. Supported formats: pdf, json, xml"
            )
        
        # In a real implementation, we would:
        # 1. Check if report exists in storage
        # 2. Retrieve report content
        # 3. Return as streaming response
        
        # For now, generate report on-demand
        from ...core.models import MetadataAnalysis, RiskLevel
        from datetime import datetime
        import io
        
        mock_metadata = MetadataAnalysis(
            document_id=doc_id,
            extracted_metadata={"mock": "data for download"}
        )
        
        mock_analysis_results = AnalysisResults(
            document_id=doc_id,
            metadata_analysis=mock_metadata,
            overall_risk_assessment=RiskLevel.LOW,
            confidence_score=0.85,
            timestamp=datetime.utcnow()
        )
        
        report_content = await report_manager.generate_report(
            analysis_results=mock_analysis_results,
            report_format=report_format,
            include_visual_evidence=True,
            include_technical_details=True
        )
        
        # Determine content type and filename
        content_types = {
            ReportFormat.PDF: "application/pdf",
            ReportFormat.JSON: "application/json",
            ReportFormat.XML: "application/xml"
        }
        
        extensions = {
            ReportFormat.PDF: "pdf",
            ReportFormat.JSON: "json",
            ReportFormat.XML: "xml"
        }
        
        content_type = content_types[report_format]
        extension = extensions[report_format]
        filename = f"forensic_report_{doc_id}.{extension}"
        
        logger.info(f"Report downloaded for document {doc_id} in {format} format by user {current_user.user_id}")
        
        return StreamingResponse(
            io.BytesIO(report_content),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report download failed for document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report download failed: {str(e)}"
        )


@router.get("/", response_model=ReportListResponse)
async def list_reports(
    page: int = 1,
    page_size: int = 20,
    format_filter: Optional[str] = None,
    current_user: User = Depends(require_read)
):
    """
    List generated reports with pagination and filtering.
    
    Requires read permissions.
    """
    try:
        # In a real implementation, this would query the database for stored reports
        # For now, we'll return mock data
        
        mock_reports = []
        for i in range(1, 21):
            report_format = "pdf" if i % 3 == 0 else "json" if i % 2 == 0 else "xml"
            mock_reports.append({
                "document_id": i,
                "format": report_format,
                "size_bytes": 1024 * (i + 10),
                "generated_at": f"2024-01-{i:02d}T10:00:00Z",
                "download_url": f"/api/v1/reports/{i}/download?format={report_format}"
            })
        
        # Apply format filter
        if format_filter:
            mock_reports = [
                report for report in mock_reports
                if report["format"] == format_filter.lower()
            ]
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_reports = mock_reports[start_idx:end_idx]
        
        logger.info(f"Listed {len(paginated_reports)} reports for user {current_user.user_id}")
        
        return ReportListResponse(
            reports=paginated_reports,
            total=len(mock_reports),
            page=page,
            page_size=page_size
        )
    
    except Exception as e:
        logger.error(f"Error listing reports: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list reports: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_report(
    document_id: int,
    format: Optional[str] = None,
    current_user: User = Depends(require_write)
):
    """
    Delete generated reports for a document.
    
    Requires write permissions.
    """
    try:
        # In a real implementation, this would delete stored reports from storage
        # For now, we'll just return success
        
        if format:
            message = f"Report for document {document_id} in {format} format deleted successfully"
        else:
            message = f"All reports for document {document_id} deleted successfully"
        
        logger.info(f"Reports deleted for document {document_id} by user {current_user.user_id}")
        
        return {"message": message}
    
    except Exception as e:
        logger.error(f"Error deleting reports for document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete reports: {str(e)}"
        )


@router.get("/{document_id}/chain-of-custody")
async def get_chain_of_custody_report(
    document_id: int,
    current_user: User = Depends(require_read)
):
    """
    Generate chain of custody report for a document.
    
    Requires read permissions.
    """
    try:
        # In a real implementation, we would:
        # 1. Retrieve all audit actions for the document
        # 2. Generate chain of custody documentation
        
        # Mock audit actions
        from datetime import datetime
        
        mock_audit_actions = [
            AuditAction(
                user_id=current_user.user_id,
                action="document_upload",
                details={"filename": f"document_{document_id}.pdf"},
                document_id=document_id,
                timestamp=datetime.utcnow()
            ),
            AuditAction(
                user_id=current_user.user_id,
                action="analysis_start",
                details={"analysis_type": "full"},
                document_id=document_id,
                timestamp=datetime.utcnow()
            )
        ]
        
        # Generate chain of custody report
        custody_report = await report_manager.document_chain_of_custody(
            document_id, mock_audit_actions
        )
        
        logger.info(f"Chain of custody report generated for document {document_id} by user {current_user.user_id}")
        
        return custody_report
    
    except Exception as e:
        logger.error(f"Chain of custody report failed for document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chain of custody report failed: {str(e)}"
        )


@router.get("/templates")
async def list_report_templates(
    current_user: User = Depends(require_read)
):
    """
    List available report templates.
    
    Requires read permissions.
    """
    try:
        # In a real implementation, this would list available Jinja2 templates
        templates = [
            {
                "name": "standard_forensic_report",
                "description": "Standard forensic analysis report with all sections",
                "format": "pdf",
                "includes_visual_evidence": True,
                "includes_technical_details": True
            },
            {
                "name": "executive_summary",
                "description": "Executive summary report for management",
                "format": "pdf",
                "includes_visual_evidence": False,
                "includes_technical_details": False
            },
            {
                "name": "technical_detailed",
                "description": "Detailed technical report for forensic experts",
                "format": "pdf",
                "includes_visual_evidence": True,
                "includes_technical_details": True
            },
            {
                "name": "json_export",
                "description": "Machine-readable JSON export of all findings",
                "format": "json",
                "includes_visual_evidence": False,
                "includes_technical_details": True
            }
        ]
        
        return {"templates": templates}
    
    except Exception as e:
        logger.error(f"Error listing report templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list report templates: {str(e)}"
        )