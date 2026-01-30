"""Workflow orchestration for document forensics analysis pipeline."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import time
from pathlib import Path

from ..core.models import (
    AnalysisResults, BatchStatus, ProcessingStatus, RiskLevel,
    MetadataAnalysis, TamperingAnalysis, AuthenticityAnalysis, VisualEvidence
)
from ..analysis.metadata_extractor import MetadataExtractor
from ..analysis.tampering_detector import TamperingDetector
from ..analysis.authenticity_scorer import AuthenticityScorer
from ..reporting.report_manager import ReportManager

logger = logging.getLogger(__name__)


class WorkflowManager:
    """Orchestrates the complete document forensics analysis pipeline."""
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize the workflow manager.
        
        Args:
            max_workers: Maximum number of parallel workers for batch processing
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Initialize analysis components
        self.metadata_extractor = MetadataExtractor()
        self.tampering_detector = TamperingDetector()
        self.authenticity_scorer = AuthenticityScorer()
        self.report_manager = ReportManager()
        
        # Progress tracking - using string IDs for batches
        self.batch_progress: Dict[str, BatchStatus] = {}
        self.document_progress: Dict[int, Dict[str, Any]] = {}
        
        # Error handling and recovery
        self.retry_attempts = 3
        self.error_handlers: Dict[str, Callable] = {}
    
    async def analyze_document(
        self,
        document_path: str,
        document_id: int,
        priority: int = 5,
        include_metadata: bool = True,
        include_tampering: bool = True,
        include_authenticity: bool = True,
        reference_samples: Optional[List[str]] = None
    ) -> AnalysisResults:
        """
        Perform complete forensic analysis on a single document.
        
        Args:
            document_path: Path to the document file
            document_id: Unique document identifier
            priority: Processing priority (1-10, higher = more priority)
            include_metadata: Whether to perform metadata analysis
            include_tampering: Whether to perform tampering detection
            include_authenticity: Whether to perform authenticity scoring
            reference_samples: Optional reference samples for authenticity comparison
            
        Returns:
            Complete analysis results
        """
        logger.info(f"Starting analysis for document {document_id} (priority: {priority})")
        
        start_time = datetime.utcnow()
        
        # Initialize progress tracking
        self.document_progress[document_id] = {
            'status': ProcessingStatus.PROCESSING,
            'start_time': start_time,
            'current_step': 'initialization',
            'progress_percentage': 0.0,
            'errors': []
        }
        
        try:
            # Validate document exists
            if not Path(document_path).exists():
                raise FileNotFoundError(f"Document not found: {document_path}")
            
            # Initialize analysis results with minimal metadata to satisfy validation
            from ..core.models import MetadataAnalysis
            
            initial_metadata = MetadataAnalysis(
                document_id=document_id,
                extracted_metadata={"status": "processing", "document_path": document_path}
            )
            
            analysis_results = AnalysisResults(
                document_id=document_id,
                metadata_analysis=initial_metadata,
                overall_risk_assessment=RiskLevel.LOW,
                confidence_score=0.0
            )
            
            total_steps = sum([include_metadata, include_tampering, include_authenticity])
            current_step = 0
            
            # Metadata Analysis
            if include_metadata:
                current_step += 1
                self._update_progress(document_id, 'metadata_analysis', (current_step / total_steps) * 0.8)
                
                try:
                    metadata_analysis = await self.metadata_extractor.extract_metadata(
                        document_path, document_id
                    )
                    analysis_results.metadata_analysis = metadata_analysis
                    logger.info(f"Metadata analysis completed for document {document_id}")
                except Exception as e:
                    logger.error(f"Metadata analysis failed for document {document_id}: {str(e)}")
                    self._record_error(document_id, 'metadata_analysis', str(e))
            
            # Tampering Detection
            if include_tampering:
                current_step += 1
                self._update_progress(document_id, 'tampering_detection', (current_step / total_steps) * 0.8)
                
                try:
                    tampering_analysis = await self.tampering_detector.detect_tampering(
                        document_path, document_id
                    )
                    analysis_results.tampering_analysis = tampering_analysis
                    
                    # Generate visual evidence if tampering detected
                    if tampering_analysis.detected_modifications:
                        visual_evidence = await self.tampering_detector.generate_tampering_heatmap(
                            document_path, tampering_analysis
                        )
                        analysis_results.visual_evidence.append(visual_evidence)
                    
                    logger.info(f"Tampering detection completed for document {document_id}")
                except Exception as e:
                    logger.error(f"Tampering detection failed for document {document_id}: {str(e)}")
                    self._record_error(document_id, 'tampering_detection', str(e))
            
            # Authenticity Scoring
            if include_authenticity:
                current_step += 1
                self._update_progress(document_id, 'authenticity_scoring', (current_step / total_steps) * 0.8)
                
                try:
                    authenticity_analysis = await self.authenticity_scorer.calculate_authenticity_score(
                        document_path, document_id, reference_samples
                    )
                    analysis_results.authenticity_analysis = authenticity_analysis
                    logger.info(f"Authenticity scoring completed for document {document_id}")
                except Exception as e:
                    logger.error(f"Authenticity scoring failed for document {document_id}: {str(e)}")
                    self._record_error(document_id, 'authenticity_scoring', str(e))
            
            # Calculate overall assessment
            self._update_progress(document_id, 'finalization', 0.9)
            analysis_results = self._calculate_overall_assessment(analysis_results)
            
            # Calculate processing time
            end_time = datetime.utcnow()
            analysis_results.processing_time = (end_time - start_time).total_seconds()
            
            # Update final progress
            self._update_progress(document_id, 'completed', 1.0)
            self.document_progress[document_id]['status'] = ProcessingStatus.COMPLETED
            
            logger.info(f"Analysis completed for document {document_id} in {analysis_results.processing_time:.2f}s")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Analysis failed for document {document_id}: {str(e)}")
            self.document_progress[document_id]['status'] = ProcessingStatus.FAILED
            self._record_error(document_id, 'general', str(e))
            
            # Return minimal results on failure with at least one analysis result
            from ..core.models import MetadataAnalysis
            
            minimal_metadata = MetadataAnalysis(
                document_id=document_id,
                extracted_metadata={"error": "Analysis failed", "reason": str(e)}
            )
            
            return AnalysisResults(
                document_id=document_id,
                metadata_analysis=minimal_metadata,
                overall_risk_assessment=RiskLevel.LOW,
                confidence_score=0.0,
                processing_time=(datetime.utcnow() - start_time).total_seconds()
            )
    
    async def process_batch(
        self,
        document_paths: List[str],
        document_ids: List[int],
        batch_id: Optional[str] = None,
        priority_order: Optional[List[int]] = None,
        **analysis_options
    ) -> Dict[int, AnalysisResults]:
        """
        Process multiple documents in parallel with batch coordination.
        
        Args:
            document_paths: List of document file paths
            document_ids: List of corresponding document IDs
            batch_id: Optional batch identifier (string)
            priority_order: Optional priority values for each document
            **analysis_options: Options passed to individual document analysis
            
        Returns:
            Dictionary mapping document IDs to analysis results
        """
        if len(document_paths) != len(document_ids):
            raise ValueError("Document paths and IDs lists must have the same length")
        
        batch_id = batch_id or str(int(time.time() * 1000000))
        total_documents = len(document_paths)
        
        logger.info(f"Starting batch processing {batch_id} with {total_documents} documents")
        
        # Initialize batch status
        batch_status = BatchStatus(
            batch_id=batch_id,
            status=ProcessingStatus.PROCESSING,
            total_documents=total_documents,
            processed_documents=0,
            failed_documents=0,
            progress_percentage=0.0,
            created_at=datetime.utcnow()
        )
        self.batch_progress[batch_id] = batch_status
        
        # Prepare document processing tasks
        tasks = []
        priorities = priority_order or [5] * total_documents
        
        # Sort by priority if specified
        if priority_order:
            sorted_items = sorted(
                zip(document_paths, document_ids, priorities),
                key=lambda x: x[2],
                reverse=True  # Higher priority first
            )
            document_paths, document_ids, priorities = zip(*sorted_items)
        
        # Create analysis tasks
        for doc_path, doc_id, priority in zip(document_paths, document_ids, priorities):
            task = self.analyze_document(
                document_path=doc_path,
                document_id=doc_id,
                priority=priority,
                **analysis_options
            )
            tasks.append((doc_id, task))
        
        # Process documents with controlled parallelism
        results = {}
        completed_count = 0
        failed_count = 0
        
        # Use semaphore to limit concurrent processing
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_with_semaphore(doc_id: int, task):
            async with semaphore:
                try:
                    result = await task
                    return doc_id, result, None
                except Exception as e:
                    return doc_id, None, str(e)
        
        # Execute tasks with progress tracking
        semaphore_tasks = [process_with_semaphore(doc_id, task) for doc_id, task in tasks]
        
        for completed_task in asyncio.as_completed(semaphore_tasks):
            doc_id, result, error = await completed_task
            
            if error:
                logger.error(f"Document {doc_id} processing failed: {error}")
                failed_count += 1
            else:
                # Check if the document processing actually failed by checking status
                doc_status = self.document_progress.get(doc_id, {}).get('status')
                if doc_status == ProcessingStatus.FAILED:
                    logger.error(f"Document {doc_id} analysis failed internally")
                    failed_count += 1
                else:
                    results[doc_id] = result
                    completed_count += 1
            
            # Update batch progress
            total_processed = completed_count + failed_count
            progress_percentage = (total_processed / total_documents) * 100
            
            batch_status.processed_documents = completed_count
            batch_status.failed_documents = failed_count
            batch_status.progress_percentage = progress_percentage
            batch_status.updated_at = datetime.utcnow()
            
            logger.info(f"Batch {batch_id} progress: {total_processed}/{total_documents} ({progress_percentage:.1f}%)")
        
        # Finalize batch status
        batch_status.status = ProcessingStatus.COMPLETED
        batch_status.updated_at = datetime.utcnow()
        
        logger.info(f"Batch processing {batch_id} completed: {completed_count} successful, {failed_count} failed")
        return results
    
    def get_batch_status(self, batch_id: str) -> Optional[BatchStatus]:
        """Get current status of a batch processing operation."""
        return self.batch_progress.get(batch_id)
    
    def get_document_progress(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Get current progress of a document analysis."""
        return self.document_progress.get(document_id)
    
    def _update_progress(self, document_id: int, step: str, percentage: float):
        """Update progress tracking for a document."""
        if document_id in self.document_progress:
            self.document_progress[document_id].update({
                'current_step': step,
                'progress_percentage': percentage * 100,
                'last_update': datetime.utcnow()
            })
    
    def _record_error(self, document_id: int, component: str, error_message: str):
        """Record an error for a document."""
        if document_id in self.document_progress:
            self.document_progress[document_id]['errors'].append({
                'component': component,
                'error': error_message,
                'timestamp': datetime.utcnow()
            })
    
    def _calculate_overall_assessment(self, analysis_results: AnalysisResults) -> AnalysisResults:
        """Calculate overall risk assessment and confidence score."""
        risk_scores = []
        confidence_scores = []
        
        # Collect risk and confidence from each analysis
        if analysis_results.metadata_analysis:
            # Metadata contributes to overall assessment
            if analysis_results.metadata_analysis.anomalies:
                risk_level = max([a.severity for a in analysis_results.metadata_analysis.anomalies])
                risk_scores.append(self._risk_to_numeric(risk_level))
            confidence_scores.append(0.8)  # Base confidence for metadata
        
        if analysis_results.tampering_analysis:
            risk_scores.append(self._risk_to_numeric(analysis_results.tampering_analysis.overall_risk))
            confidence_scores.append(analysis_results.tampering_analysis.confidence_score)
        
        if analysis_results.authenticity_analysis:
            auth_risk = analysis_results.authenticity_analysis.authenticity_score.risk_assessment
            risk_scores.append(self._risk_to_numeric(auth_risk))
            confidence_scores.append(analysis_results.authenticity_analysis.authenticity_score.confidence_level)
        
        # Calculate overall metrics
        if risk_scores:
            avg_risk = sum(risk_scores) / len(risk_scores)
            analysis_results.overall_risk_assessment = self._numeric_to_risk(avg_risk)
        
        if confidence_scores:
            analysis_results.confidence_score = sum(confidence_scores) / len(confidence_scores)
        
        return analysis_results
    
    def _risk_to_numeric(self, risk_level: RiskLevel) -> float:
        """Convert risk level to numeric value for calculation."""
        risk_map = {
            RiskLevel.LOW: 0.25,
            RiskLevel.MEDIUM: 0.5,
            RiskLevel.HIGH: 0.75,
            RiskLevel.CRITICAL: 1.0
        }
        return risk_map.get(risk_level, 0.25)
    
    def _numeric_to_risk(self, numeric_risk: float) -> RiskLevel:
        """Convert numeric risk back to risk level."""
        if numeric_risk >= 0.875:
            return RiskLevel.CRITICAL
        elif numeric_risk >= 0.625:
            return RiskLevel.HIGH
        elif numeric_risk >= 0.375:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    async def generate_batch_report(
        self,
        batch_results: Dict[int, AnalysisResults],
        batch_id: str,
        output_path: Optional[str] = None
    ) -> bytes:
        """Generate comprehensive report for batch processing results."""
        try:
            # Generate statistical summary
            results_list = list(batch_results.values())
            statistical_summary = await self.report_manager.generate_statistical_summary(results_list)
            
            # Create batch report data
            batch_report_data = {
                'batch_id': str(batch_id),
                'generated_at': datetime.utcnow().isoformat(),
                'total_documents': len(batch_results),
                'statistical_summary': statistical_summary,
                'individual_results': {
                    str(doc_id): result.model_dump() if hasattr(result, 'model_dump') else result.__dict__
                    for doc_id, result in batch_results.items()
                }
            }
            
            # Generate JSON report for batch
            import json
            report_content = json.dumps(batch_report_data, indent=2, default=str).encode('utf-8')
            
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(report_content)
            
            return report_content
            
        except Exception as e:
            logger.error(f"Error generating batch report: {str(e)}")
            raise
    
    def add_error_handler(self, error_type: str, handler: Callable):
        """Add custom error handler for specific error types."""
        self.error_handlers[error_type] = handler
    
    def cleanup_completed_batches(self, max_age_hours: int = 24):
        """Clean up completed batch progress data older than specified hours."""
        cutoff_time = datetime.utcnow().replace(hour=datetime.utcnow().hour - max_age_hours)
        
        to_remove = []
        for batch_id, batch_status in self.batch_progress.items():
            if (batch_status.status == ProcessingStatus.COMPLETED and 
                batch_status.updated_at and 
                batch_status.updated_at < cutoff_time):
                to_remove.append(batch_id)
        
        for batch_id in to_remove:
            del self.batch_progress[batch_id]
        
        logger.info(f"Cleaned up {len(to_remove)} completed batch records")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status and statistics."""
        active_batches = sum(1 for status in self.batch_progress.values() 
                           if status.status == ProcessingStatus.PROCESSING)
        
        active_documents = sum(1 for progress in self.document_progress.values()
                             if progress['status'] == ProcessingStatus.PROCESSING)
        
        return {
            'active_batches': active_batches,
            'active_documents': active_documents,
            'total_batches_tracked': len(self.batch_progress),
            'total_documents_tracked': len(self.document_progress),
            'max_workers': self.max_workers,
            'system_timestamp': datetime.utcnow().isoformat()
        }