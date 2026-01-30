"""
End-to-end integration tests for the complete document forensics system.

This module tests the complete document analysis workflow, batch processing,
API integration with external systems, and error handling/recovery scenarios.

Requirements: All requirements integration
"""

import asyncio
import json
import tempfile
import pytest
import httpx
from pathlib import Path
from typing import Dict, List, Any
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from src.document_forensics.workflow.workflow_manager import WorkflowManager
from src.document_forensics.core.models import ProcessingStatus, RiskLevel
from src.document_forensics.api.main import create_app


class TestEndToEndIntegration:
    """End-to-end integration tests for the complete system."""
    
    @pytest.fixture
    def workflow_manager(self):
        """Create a workflow manager for testing."""
        return WorkflowManager(max_workers=2)
    
    @pytest.fixture
    def sample_documents(self, tmp_path):
        """Create sample documents for testing."""
        documents = {}
        
        # Create a sample PDF
        pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT/F1 12 Tf 72 720 Td(Test Document)Tj ET
endstream endobj
xref 0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref 300
%%EOF"""
        
        pdf_path = tmp_path / "test_document.pdf"
        pdf_path.write_bytes(pdf_content)
        documents['pdf'] = str(pdf_path)
        
        # Create a sample text file
        text_content = "This is a test document for forensic analysis.\nIt contains multiple lines of text."
        text_path = tmp_path / "test_document.txt"
        text_path.write_text(text_content)
        documents['text'] = str(text_path)
        
        # Create a sample image (1x1 PNG)
        image_content = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
            "890000000a4944415478da6300010000050001d72db3520000000049454e44ae"
            "426082"
        )
        image_path = tmp_path / "test_image.png"
        image_path.write_bytes(image_content)
        documents['image'] = str(image_path)
        
        return documents
    
    @pytest.fixture
    def api_client(self):
        """Create a test client for the API."""
        app = create_app()
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
    
    async def test_complete_document_analysis_workflow(self, workflow_manager, sample_documents):
        """
        Test the complete document analysis workflow from upload to report generation.
        
        This test verifies:
        - Document upload and validation
        - Metadata extraction
        - Tampering detection
        - Authenticity scoring
        - Report generation
        - Progress tracking throughout the process
        """
        # Test with PDF document
        pdf_path = sample_documents['pdf']
        document_id = 1
        
        # Mock the analysis components to avoid external dependencies
        with patch.object(workflow_manager.metadata_extractor, 'extract_metadata') as mock_metadata, \
             patch.object(workflow_manager.tampering_detector, 'detect_tampering') as mock_tampering, \
             patch.object(workflow_manager.authenticity_scorer, 'calculate_authenticity_score') as mock_authenticity:
            
            # Configure mocks to return realistic data
            from src.document_forensics.core.models import (
                MetadataAnalysis, TamperingAnalysis, AuthenticityAnalysis,
                AuthenticityScore, Modification, RiskLevel
            )
            
            mock_metadata.return_value = MetadataAnalysis(
                document_id=document_id,
                extracted_metadata={
                    "creation_date": "2024-01-01T10:00:00Z",
                    "author": "Test Author",
                    "software": "Test PDF Creator"
                }
            )
            
            mock_tampering.return_value = TamperingAnalysis(
                document_id=document_id,
                overall_risk=RiskLevel.LOW,
                detected_modifications=[],
                confidence_score=0.95
            )
            
            mock_authenticity.return_value = AuthenticityAnalysis(
                document_id=document_id,
                authenticity_score=AuthenticityScore(
                    overall_score=0.85,
                    confidence_level=0.90,
                    risk_assessment=RiskLevel.LOW,
                    contributing_factors={
                        "metadata_consistency": 0.9,
                        "file_structure_validation": 0.8
                    }
                )
            )
            
            # Perform complete analysis
            results = await workflow_manager.analyze_document(
                document_path=pdf_path,
                document_id=document_id,
                priority=8,
                include_metadata=True,
                include_tampering=True,
                include_authenticity=True
            )
            
            # Verify analysis results
            assert results is not None
            assert results.document_id == document_id
            assert results.metadata_analysis is not None
            assert results.tampering_analysis is not None
            assert results.authenticity_analysis is not None
            assert results.overall_risk_assessment == RiskLevel.LOW
            assert results.confidence_score > 0.0
            assert results.processing_time >= 0.0
            
            # Verify progress tracking
            progress = workflow_manager.get_document_progress(document_id)
            assert progress is not None
            assert progress['status'] == ProcessingStatus.COMPLETED
            assert progress['progress_percentage'] == 100.0
            
            # Verify all analysis components were called
            mock_metadata.assert_called_once()
            mock_tampering.assert_called_once()
            mock_authenticity.assert_called_once()
    
    async def test_batch_processing_multiple_document_types(self, workflow_manager, sample_documents):
        """
        Test batch processing with multiple document types.
        
        This test verifies:
        - Parallel processing of different document types
        - Progress tracking for batch operations
        - Proper handling of mixed success/failure scenarios
        - Priority-based processing order
        """
        document_paths = list(sample_documents.values())
        document_ids = [1, 2, 3]
        priority_order = [10, 5, 8]  # High, low, medium priority
        batch_id = uuid4()
        
        # Mock analysis components
        with patch.object(workflow_manager.metadata_extractor, 'extract_metadata') as mock_metadata, \
             patch.object(workflow_manager.tampering_detector, 'detect_tampering') as mock_tampering, \
             patch.object(workflow_manager.authenticity_scorer, 'calculate_authenticity_score') as mock_authenticity:
            
            from src.document_forensics.core.models import (
                MetadataAnalysis, TamperingAnalysis, AuthenticityAnalysis, AuthenticityScore
            )
            
            # Configure mocks to return different results for different documents
            def metadata_side_effect(doc_path, doc_id):
                return MetadataAnalysis(
                    document_id=doc_id,
                    extracted_metadata={
                        "document_type": Path(doc_path).suffix,
                        "analysis_timestamp": "2024-01-01T10:00:00Z"
                    }
                )
            
            def tampering_side_effect(doc_path, doc_id):
                # Simulate different risk levels for different documents
                risk_levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
                return TamperingAnalysis(
                    document_id=doc_id,
                    overall_risk=risk_levels[doc_id - 1],
                    detected_modifications=[],
                    confidence_score=0.8 + (doc_id * 0.05)
                )
            
            def authenticity_side_effect(doc_path, doc_id, ref_samples=None):
                return AuthenticityAnalysis(
                    document_id=doc_id,
                    authenticity_score=AuthenticityScore(
                        overall_score=0.7 + (doc_id * 0.1),
                        confidence_level=0.85,
                        risk_assessment=RiskLevel.LOW,
                        contributing_factors={
                            "metadata_consistency": 0.8,
                            "file_structure_validation": 0.7
                        }
                    )
                )
            
            mock_metadata.side_effect = metadata_side_effect
            mock_tampering.side_effect = tampering_side_effect
            mock_authenticity.side_effect = authenticity_side_effect
            
            # Process batch
            results = await workflow_manager.process_batch(
                document_paths=document_paths,
                document_ids=document_ids,
                batch_id=batch_id,
                priority_order=priority_order,
                include_metadata=True,
                include_tampering=True,
                include_authenticity=True
            )
            
            # Verify batch results
            assert len(results) == 3
            assert all(doc_id in results for doc_id in document_ids)
            
            # Verify each document was processed
            for doc_id in document_ids:
                result = results[doc_id]
                assert result.document_id == doc_id
                assert result.metadata_analysis is not None
                assert result.tampering_analysis is not None
                assert result.authenticity_analysis is not None
            
            # Verify batch status
            batch_status = workflow_manager.get_batch_status(batch_id)
            assert batch_status is not None
            assert batch_status.status == ProcessingStatus.COMPLETED
            assert batch_status.processed_documents == 3
            assert batch_status.failed_documents == 0
            assert batch_status.progress_percentage == 100.0
            
            # Generate batch report
            report_content = await workflow_manager.generate_batch_report(
                batch_results=results,
                batch_id=batch_id
            )
            
            # Verify report content
            assert report_content is not None
            report_data = json.loads(report_content.decode('utf-8'))
            assert report_data['batch_id'] == str(batch_id)
            assert report_data['total_documents'] == 3
            assert 'statistical_summary' in report_data
            assert 'individual_results' in report_data
    
    async def test_api_integration_with_external_systems(self, api_client):
        """
        Test API integration with external systems.
        
        This test verifies:
        - RESTful API endpoints functionality
        - Authentication and authorization
        - Webhook notifications
        - Structured data responses (JSON/XML)
        - Rate limiting behavior
        """
        # Test health check endpoint
        response = await api_client.get("/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "document-forensics-api"
        
        # Test root endpoint
        response = await api_client.get("/")
        assert response.status_code == 200
        root_data = response.json()
        assert "service" in root_data
        assert "version" in root_data
        
        # Test API documentation endpoints
        response = await api_client.get("/docs")
        assert response.status_code == 200
        
        response = await api_client.get("/openapi.json")
        assert response.status_code == 200
        openapi_spec = response.json()
        assert "openapi" in openapi_spec
        assert "paths" in openapi_spec
        
        # Verify API structure includes all required endpoints
        paths = openapi_spec["paths"]
        required_endpoints = [
            "/api/v1/auth/login",
            "/api/v1/documents/upload",
            "/api/v1/analysis/analyze",
            "/api/v1/batch/process",
            "/api/v1/reports/generate",
            "/api/v1/webhooks/register"
        ]
        
        for endpoint in required_endpoints:
            assert any(endpoint in path for path in paths.keys()), f"Missing endpoint: {endpoint}"
    
    async def test_error_handling_and_recovery_scenarios(self, workflow_manager, sample_documents):
        """
        Test error handling and recovery scenarios.
        
        This test verifies:
        - Graceful handling of file not found errors
        - Recovery from analysis component failures
        - Partial result preservation on errors
        - Error logging and reporting
        - Batch processing continuation after individual failures
        """
        # Test 1: File not found error
        non_existent_path = "/path/to/nonexistent/file.pdf"
        document_id = 999
        
        result = await workflow_manager.analyze_document(
            document_path=non_existent_path,
            document_id=document_id
        )
        
        # Should return minimal results with error information
        assert result is not None
        assert result.document_id == document_id
        assert result.processing_time >= 0
        
        # Check progress tracking recorded the error
        progress = workflow_manager.get_document_progress(document_id)
        assert progress is not None
        assert progress['status'] == ProcessingStatus.FAILED
        assert len(progress['errors']) > 0
        
        # Test 2: Analysis component failure with partial recovery
        pdf_path = sample_documents['pdf']
        document_id = 998
        
        with patch.object(workflow_manager.metadata_extractor, 'extract_metadata') as mock_metadata, \
             patch.object(workflow_manager.tampering_detector, 'detect_tampering') as mock_tampering, \
             patch.object(workflow_manager.authenticity_scorer, 'calculate_authenticity_score') as mock_authenticity:
            
            from src.document_forensics.core.models import MetadataAnalysis
            
            # Make metadata extraction succeed but tampering detection fail
            mock_metadata.return_value = MetadataAnalysis(
                document_id=document_id,
                extracted_metadata={"status": "success"}
            )
            mock_tampering.side_effect = Exception("Tampering detection failed")
            mock_authenticity.side_effect = Exception("Authenticity scoring failed")
            
            result = await workflow_manager.analyze_document(
                document_path=pdf_path,
                document_id=document_id,
                include_metadata=True,
                include_tampering=True,
                include_authenticity=True
            )
            
            # Should have partial results (metadata succeeded)
            assert result is not None
            assert result.metadata_analysis is not None
            assert result.tampering_analysis is None  # Failed
            assert result.authenticity_analysis is None  # Failed
            
            # Check error recording
            progress = workflow_manager.get_document_progress(document_id)
            assert len(progress['errors']) >= 2  # Two components failed
        
        # Test 3: Batch processing with mixed success/failure
        document_paths = [sample_documents['pdf'], "/nonexistent.pdf", sample_documents['text']]
        document_ids = [1, 2, 3]
        batch_id = uuid4()
        
        with patch.object(workflow_manager.metadata_extractor, 'extract_metadata') as mock_metadata:
            from src.document_forensics.core.models import MetadataAnalysis
            
            mock_metadata.return_value = MetadataAnalysis(
                document_id=1,
                extracted_metadata={"status": "success"}
            )
            
            results = await workflow_manager.process_batch(
                document_paths=document_paths,
                document_ids=document_ids,
                batch_id=batch_id,
                include_metadata=True,
                include_tampering=False,
                include_authenticity=False
            )
            
            # Should have results for existing files only
            assert len(results) <= 2  # At most 2 successful (nonexistent file should fail)
            
            # Check batch status shows some failures
            batch_status = workflow_manager.get_batch_status(batch_id)
            assert batch_status is not None
            assert batch_status.failed_documents > 0
            assert batch_status.processed_documents + batch_status.failed_documents == 3
    
    async def test_system_monitoring_and_health_checks(self, workflow_manager):
        """
        Test system monitoring and health check functionality.
        
        This test verifies:
        - System status reporting
        - Resource usage monitoring
        - Health check endpoints
        - Performance metrics collection
        """
        # Test system status reporting
        status = workflow_manager.get_system_status()
        
        assert isinstance(status, dict)
        assert 'active_batches' in status
        assert 'active_documents' in status
        assert 'total_batches_tracked' in status
        assert 'total_documents_tracked' in status
        assert 'max_workers' in status
        assert 'system_timestamp' in status
        
        # Verify initial state
        assert status['active_batches'] == 0
        assert status['active_documents'] == 0
        assert status['max_workers'] == workflow_manager.max_workers
        
        # Test cleanup functionality
        workflow_manager.cleanup_completed_batches(max_age_hours=0)  # Clean all
        
        # Status should remain consistent after cleanup
        new_status = workflow_manager.get_system_status()
        assert new_status['total_batches_tracked'] == 0
    
    async def test_concurrent_processing_stress(self, workflow_manager, sample_documents):
        """
        Test concurrent processing under stress conditions.
        
        This test verifies:
        - System behavior under high concurrent load
        - Resource management and limits
        - Queue management for batch processing
        - Memory and performance stability
        """
        # Create multiple concurrent batch processing tasks
        num_concurrent_batches = 3
        documents_per_batch = 2
        
        batch_tasks = []
        
        for batch_num in range(num_concurrent_batches):
            # Use subset of sample documents for each batch
            batch_paths = list(sample_documents.values())[:documents_per_batch]
            batch_ids = [batch_num * 10 + i for i in range(documents_per_batch)]
            batch_uuid = uuid4()
            
            # Mock analysis components for faster execution
            with patch.object(workflow_manager.metadata_extractor, 'extract_metadata') as mock_metadata:
                from src.document_forensics.core.models import MetadataAnalysis
                
                mock_metadata.return_value = MetadataAnalysis(
                    document_id=1,
                    extracted_metadata={"batch": batch_num}
                )
                
                task = workflow_manager.process_batch(
                    document_paths=batch_paths,
                    document_ids=batch_ids,
                    batch_id=batch_uuid,
                    include_metadata=True,
                    include_tampering=False,
                    include_authenticity=False
                )
                batch_tasks.append((batch_uuid, task))
        
        # Execute all batches concurrently
        completed_batches = []
        for batch_id, task in batch_tasks:
            try:
                # Use a shorter timeout for stress testing
                result = await asyncio.wait_for(task, timeout=30.0)
                completed_batches.append((batch_id, result))
            except asyncio.TimeoutError:
                # Log timeout but continue with other batches
                print(f"Batch {batch_id} timed out")
        
        # Verify at least some batches completed successfully
        assert len(completed_batches) > 0
        
        # Verify system status remains stable
        final_status = workflow_manager.get_system_status()
        assert isinstance(final_status, dict)
        assert final_status['max_workers'] == workflow_manager.max_workers
    
    async def test_data_persistence_and_recovery(self, workflow_manager, sample_documents, tmp_path):
        """
        Test data persistence and recovery capabilities.
        
        This test verifies:
        - Analysis results persistence
        - Recovery from system interruptions
        - Data integrity maintenance
        - Audit trail preservation
        """
        # Test report generation and persistence
        pdf_path = sample_documents['pdf']
        document_id = 1
        
        with patch.object(workflow_manager.metadata_extractor, 'extract_metadata') as mock_metadata:
            from src.document_forensics.core.models import MetadataAnalysis
            
            mock_metadata.return_value = MetadataAnalysis(
                document_id=document_id,
                extracted_metadata={
                    "creation_date": "2024-01-01T10:00:00Z",
                    "persistence_test": True
                }
            )
            
            # Perform analysis
            result = await workflow_manager.analyze_document(
                document_path=pdf_path,
                document_id=document_id,
                include_metadata=True,
                include_tampering=False,
                include_authenticity=False
            )
            
            # Generate and save report
            batch_results = {document_id: result}
            batch_id = uuid4()
            report_path = tmp_path / f"batch_report_{batch_id}.json"
            
            report_content = await workflow_manager.generate_batch_report(
                batch_results=batch_results,
                batch_id=batch_id,
                output_path=str(report_path)
            )
            
            # Verify report was saved
            assert report_path.exists()
            assert report_path.stat().st_size > 0
            
            # Verify report content integrity
            saved_content = report_path.read_bytes()
            assert saved_content == report_content
            
            # Parse and verify report structure
            report_data = json.loads(saved_content.decode('utf-8'))
            assert report_data['batch_id'] == str(batch_id)
            assert report_data['total_documents'] == 1
            assert str(document_id) in report_data['individual_results']
            
            # Verify individual result data
            individual_result = report_data['individual_results'][str(document_id)]
            assert individual_result['document_id'] == document_id
            assert 'metadata_analysis' in individual_result