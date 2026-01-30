"""Property-based tests for workflow management functionality."""

import asyncio
import tempfile
from pathlib import Path
from typing import List, Dict, Any
from uuid import uuid4
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from src.document_forensics.workflow.workflow_manager import WorkflowManager
from src.document_forensics.core.models import (
    AnalysisResults, BatchStatus, ProcessingStatus, RiskLevel, MetadataAnalysis
)


class TestWorkflowManager:
    """Property-based tests for workflow management."""
    
    @pytest.fixture
    def workflow_manager(self):
        """Create a workflow manager instance."""
        return WorkflowManager(max_workers=2)
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    def create_test_document(self, temp_dir: str, filename: str, content: str = "Test content") -> str:
        """Create a test document file."""
        file_path = Path(temp_dir) / filename
        file_path.write_text(content)
        return str(file_path)
    
    @given(
        num_documents=st.integers(min_value=1, max_value=5),
        priorities=st.lists(st.integers(min_value=1, max_value=10), min_size=1, max_size=5)
    )
    @settings(max_examples=8, deadline=30000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_batch_processing_reliability(
        self, workflow_manager, temp_dir, num_documents, priorities
    ):
        """
        **Feature: document-forensics, Property 7: Batch Processing Reliability**
        **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
        
        For any batch of documents submitted for processing, the system should process 
        them in parallel, track progress accurately, handle errors gracefully without 
        stopping the batch, and generate comprehensive summary reports.
        """
        assume(len(priorities) >= num_documents)
        
        # Create test documents
        document_paths = []
        document_ids = []
        
        for i in range(num_documents):
            doc_path = self.create_test_document(temp_dir, f"test_doc_{i}.txt", f"Content {i}")
            document_paths.append(doc_path)
            document_ids.append(i + 1)
        
        # Use priorities up to num_documents
        doc_priorities = priorities[:num_documents]
        
        # Process batch
        batch_id = uuid4()
        results = await workflow_manager.process_batch(
            document_paths=document_paths,
            document_ids=document_ids,
            batch_id=batch_id,
            priority_order=doc_priorities,
            include_metadata=True,
            include_tampering=False,  # Simplified for testing
            include_authenticity=False
        )
        
        # Verify batch processing reliability
        assert isinstance(results, dict)
        assert len(results) <= num_documents  # May have failures, but should not exceed input
        
        # Verify all successful results are valid
        for doc_id, result in results.items():
            assert isinstance(result, AnalysisResults)
            assert result.document_id == doc_id
            assert isinstance(result.confidence_score, float)
            assert 0.0 <= result.confidence_score <= 1.0
            assert isinstance(result.overall_risk_assessment, RiskLevel)
        
        # Verify batch status tracking
        batch_status = workflow_manager.get_batch_status(batch_id)
        assert isinstance(batch_status, BatchStatus)
        assert batch_status.batch_id == str(batch_id)  # Compare as strings since batch_id is converted to str
        assert batch_status.total_documents == num_documents
        assert batch_status.status == ProcessingStatus.COMPLETED
        assert batch_status.processed_documents + batch_status.failed_documents == num_documents
        assert 0.0 <= batch_status.progress_percentage <= 100.0
        
        # Verify progress tracking accuracy
        total_processed = batch_status.processed_documents + batch_status.failed_documents
        expected_percentage = (total_processed / num_documents) * 100
        assert abs(batch_status.progress_percentage - expected_percentage) < 0.1
        
        # Verify error handling (system should continue processing despite individual failures)
        # The batch should complete even if some documents fail
        assert batch_status.status == ProcessingStatus.COMPLETED
    
    @given(
        document_id=st.integers(min_value=1, max_value=1000),
        priority=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=10, deadline=20000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_progress_tracking_consistency(
        self, workflow_manager, temp_dir, document_id, priority
    ):
        """
        **Feature: document-forensics, Property 8: Progress Tracking Consistency**
        **Validates: Requirements 1.4, 6.2**
        
        For any document or batch being processed, the system should provide real-time 
        progress updates that accurately reflect the current processing state and 
        completion percentage.
        """
        # Create test document
        doc_path = self.create_test_document(temp_dir, "test_doc.txt")
        
        # Start analysis (this will update progress)
        analysis_task = asyncio.create_task(
            workflow_manager.analyze_document(
                document_path=doc_path,
                document_id=document_id,
                priority=priority,
                include_metadata=True,
                include_tampering=False,
                include_authenticity=False
            )
        )
        
        # Allow some processing time
        await asyncio.sleep(0.1)
        
        # Check progress tracking during processing
        progress = workflow_manager.get_document_progress(document_id)
        
        if progress:  # Progress tracking may not be immediately available
            assert isinstance(progress, dict)
            assert 'status' in progress
            assert 'progress_percentage' in progress
            assert 'current_step' in progress
            
            # Progress percentage should be valid
            assert isinstance(progress['progress_percentage'], (int, float))
            assert 0.0 <= progress['progress_percentage'] <= 100.0
            
            # Status should be valid
            assert progress['status'] in [ProcessingStatus.PROCESSING, ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]
            
            # Current step should be a string
            assert isinstance(progress['current_step'], str)
        
        # Wait for completion
        result = await analysis_task
        
        # Verify final progress state
        final_progress = workflow_manager.get_document_progress(document_id)
        assert final_progress is not None
        assert final_progress['status'] in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]
        
        # If completed successfully, progress should be 100%
        if final_progress['status'] == ProcessingStatus.COMPLETED:
            assert final_progress['progress_percentage'] == 100.0
            assert isinstance(result, AnalysisResults)
            assert result.document_id == document_id
    
    @given(
        num_documents=st.integers(min_value=2, max_value=4),
        include_failures=st.booleans()
    )
    @settings(max_examples=6, deadline=25000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_parallel_processing_coordination(
        self, workflow_manager, temp_dir, num_documents, include_failures
    ):
        """
        Test that parallel processing coordinates properly and handles
        concurrent document analysis without conflicts.
        """
        # Create test documents (some may be invalid if include_failures is True)
        document_paths = []
        document_ids = []
        
        for i in range(num_documents):
            if include_failures and i == num_documents - 1:
                # Create invalid document path for last document
                doc_path = str(Path(temp_dir) / "nonexistent_file.txt")
            else:
                doc_path = self.create_test_document(temp_dir, f"doc_{i}.txt", f"Content {i}")
            
            document_paths.append(doc_path)
            document_ids.append(i + 1)
        
        # Process batch with parallel coordination
        batch_id = uuid4()
        results = await workflow_manager.process_batch(
            document_paths=document_paths,
            document_ids=document_ids,
            batch_id=batch_id,
            include_metadata=True,
            include_tampering=False,
            include_authenticity=False
        )
        
        # Verify parallel processing coordination
        assert isinstance(results, dict)
        
        # Should have results for valid documents
        valid_document_count = num_documents - (1 if include_failures else 0)
        assert len(results) <= num_documents
        
        # All returned results should be valid
        for doc_id, result in results.items():
            assert isinstance(result, AnalysisResults)
            assert result.document_id == doc_id
            assert result.document_id in document_ids
        
        # Verify batch coordination
        batch_status = workflow_manager.get_batch_status(batch_id)
        assert batch_status is not None
        assert batch_status.total_documents == num_documents
        assert batch_status.status == ProcessingStatus.COMPLETED
        
        # Total processed + failed should equal total documents
        total_handled = batch_status.processed_documents + batch_status.failed_documents
        assert total_handled == num_documents
        
        # If we included failures, should have at least one failure
        if include_failures:
            assert batch_status.failed_documents >= 1
    
    @pytest.mark.asyncio
    async def test_property_error_handling_robustness(self, workflow_manager, temp_dir):
        """
        Test that the workflow manager handles various error conditions gracefully
        and continues processing other documents in a batch.
        """
        # Create mix of valid and invalid documents
        valid_doc = self.create_test_document(temp_dir, "valid.txt", "Valid content")
        invalid_doc = "/nonexistent/path/invalid.txt"
        empty_doc = self.create_test_document(temp_dir, "empty.txt", "")
        
        document_paths = [valid_doc, invalid_doc, empty_doc]
        document_ids = [1, 2, 3]
        
        # Process batch with mixed validity
        batch_id = uuid4()
        results = await workflow_manager.process_batch(
            document_paths=document_paths,
            document_ids=document_ids,
            batch_id=batch_id,
            include_metadata=True,
            include_tampering=False,
            include_authenticity=False
        )
        
        # Should handle errors gracefully
        assert isinstance(results, dict)
        
        # Should have at least processed the valid document
        assert len(results) >= 1
        
        # Valid document should have successful result
        if 1 in results:
            assert isinstance(results[1], AnalysisResults)
            assert results[1].document_id == 1
        
        # Batch should complete despite errors
        batch_status = workflow_manager.get_batch_status(batch_id)
        assert batch_status is not None
        assert batch_status.status == ProcessingStatus.COMPLETED
        assert batch_status.total_documents == 3
        
        # Should have some failures recorded
        assert batch_status.failed_documents >= 1
    
    def test_system_status_reporting(self, workflow_manager):
        """Test that system status reporting provides accurate information."""
        status = workflow_manager.get_system_status()
        
        assert isinstance(status, dict)
        assert 'active_batches' in status
        assert 'active_documents' in status
        assert 'total_batches_tracked' in status
        assert 'total_documents_tracked' in status
        assert 'max_workers' in status
        assert 'system_timestamp' in status
        
        # Values should be non-negative integers
        assert isinstance(status['active_batches'], int)
        assert status['active_batches'] >= 0
        assert isinstance(status['active_documents'], int)
        assert status['active_documents'] >= 0
        assert isinstance(status['max_workers'], int)
        assert status['max_workers'] > 0
        
        # Timestamp should be a string
        assert isinstance(status['system_timestamp'], str)


# Unit tests for specific edge cases and examples
class TestWorkflowManager_Units:
    """Unit tests for specific workflow management scenarios."""
    
    @pytest.fixture
    def workflow_manager(self):
        """Create a workflow manager instance."""
        return WorkflowManager(max_workers=1)
    
    @pytest.mark.asyncio
    async def test_single_document_analysis(self, workflow_manager, tmp_path):
        """Test analysis of a single document."""
        # Create test document
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content for analysis")
        
        # Analyze document
        result = await workflow_manager.analyze_document(
            document_path=str(test_file),
            document_id=1,
            include_metadata=True,
            include_tampering=False,
            include_authenticity=False
        )
        
        # Verify result
        assert isinstance(result, AnalysisResults)
        assert result.document_id == 1
        assert isinstance(result.processing_time, float)
        assert result.processing_time >= 0  # Allow zero processing time for very fast operations
    
    @pytest.mark.asyncio
    async def test_empty_batch_processing(self, workflow_manager):
        """Test processing of empty batch."""
        results = await workflow_manager.process_batch(
            document_paths=[],
            document_ids=[],
            batch_id=uuid4()
        )
        
        assert isinstance(results, dict)
        assert len(results) == 0
    
    def test_progress_tracking_initialization(self, workflow_manager):
        """Test progress tracking initialization."""
        # Initially no progress tracked
        progress = workflow_manager.get_document_progress(999)
        assert progress is None
        
        # System status should show no active items
        status = workflow_manager.get_system_status()
        assert status['active_documents'] == 0
        assert status['active_batches'] == 0
    
    def test_batch_status_retrieval(self, workflow_manager):
        """Test batch status retrieval for non-existent batch."""
        non_existent_batch = uuid4()
        status = workflow_manager.get_batch_status(non_existent_batch)
        assert status is None
    
    def test_risk_level_calculations(self, workflow_manager):
        """Test risk level conversion utilities."""
        # Test risk to numeric conversion
        assert workflow_manager._risk_to_numeric(RiskLevel.LOW) == 0.25
        assert workflow_manager._risk_to_numeric(RiskLevel.MEDIUM) == 0.5
        assert workflow_manager._risk_to_numeric(RiskLevel.HIGH) == 0.75
        assert workflow_manager._risk_to_numeric(RiskLevel.CRITICAL) == 1.0
        
        # Test numeric to risk conversion
        assert workflow_manager._numeric_to_risk(0.1) == RiskLevel.LOW
        assert workflow_manager._numeric_to_risk(0.5) == RiskLevel.MEDIUM
        assert workflow_manager._numeric_to_risk(0.7) == RiskLevel.HIGH
        assert workflow_manager._numeric_to_risk(0.9) == RiskLevel.CRITICAL