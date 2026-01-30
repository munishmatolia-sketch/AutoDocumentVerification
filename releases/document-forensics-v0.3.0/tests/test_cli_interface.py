"""Integration tests for the CLI interface."""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

import pytest
import requests
from click.testing import CliRunner

from src.document_forensics.cli.main import (
    cli, DocumentForensicsCLI, display_analysis_results, display_batch_summary
)
from src.document_forensics.core.models import ProcessingStatus, RiskLevel


class TestCLIIntegration:
    """Integration tests for the CLI interface."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cli_obj = DocumentForensicsCLI()
        self.runner = CliRunner()
        
        self.mock_upload_response = {
            "success": True,
            "document_id": "test-doc-123",
            "document": {
                "id": 1,
                "filename": "test.pdf",
                "file_type": "pdf",
                "size": 1024,
                "processing_status": "pending"
            }
        }
        
        self.mock_analysis_results = {
            "document_id": "test-doc-123",
            "timestamp": "2024-01-15T10:00:00Z",
            "overall_risk_assessment": "medium",
            "confidence_score": 0.85,
            "processing_time": 2.5,
            "tampering_analysis": {
                "overall_risk": "medium",
                "detected_modifications": [
                    {"description": "Text modification detected", "confidence": 0.8}
                ]
            },
            "authenticity_analysis": {
                "authenticity_score": {
                    "overall_score": 0.7,
                    "confidence_level": 0.8
                }
            },
            "visual_evidence": [
                {
                    "type": "tampering_heatmap",
                    "description": "Tampering detection heatmap",
                    "confidence_level": 0.8
                }
            ]
        }
    
    @patch('requests.Session.post')
    def test_cli_upload_document_success(self, mock_post):
        """Test successful document upload through CLI."""
        # Mock successful API response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = self.mock_upload_response
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
            f.write("Test PDF content")
            temp_path = f.name
        
        try:
            result = self.cli_obj.upload_document(
                file_path=temp_path,
                description="Test document",
                tags=["test", "cli"],
                priority=7
            )
            
            assert result["success"] is True
            assert result["document_id"] == "test-doc-123"
            
            # Verify API call
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "/documents/upload" in call_args[0][0]
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @patch('requests.Session.post')
    def test_cli_upload_document_failure(self, mock_post):
        """Test failed document upload through CLI."""
        # Mock failed API response
        mock_post.return_value.status_code = 400
        mock_post.return_value.text = "Invalid file format"
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.invalid', delete=False) as f:
            f.write("Invalid content")
            temp_path = f.name
        
        try:
            result = self.cli_obj.upload_document(file_path=temp_path)
            
            assert result["success"] is False
            assert "Upload failed" in result["error"]
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_cli_upload_nonexistent_file(self):
        """Test upload of non-existent file through CLI."""
        result = self.cli_obj.upload_document("/nonexistent/file.pdf")
        
        assert result["success"] is False
        assert "File not found" in result["error"]
    
    @patch('requests.Session.post')
    def test_cli_start_analysis(self, mock_post):
        """Test starting analysis through CLI."""
        # Mock successful API response
        mock_post.return_value.status_code = 200
        
        result = self.cli_obj.start_analysis("test-doc-123")
        
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/analysis/start" in call_args[0][0]
    
    @patch('requests.Session.get')
    def test_cli_get_document_status(self, mock_get):
        """Test getting document status through CLI."""
        # Mock API response
        mock_status = {"status": "processing", "progress": 50}
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_status
        
        result = self.cli_obj.get_document_status("test-doc-123")
        
        assert result == mock_status
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "/documents/test-doc-123/status" in call_args[0][0]
    
    @patch('requests.Session.get')
    def test_cli_get_analysis_results(self, mock_get):
        """Test getting analysis results through CLI."""
        # Mock API response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.mock_analysis_results
        
        result = self.cli_obj.get_analysis_results("test-doc-123")
        
        assert result == self.mock_analysis_results
        assert result["overall_risk_assessment"] == "medium"
        assert result["confidence_score"] == 0.85
    
    @patch('requests.Session.post')
    def test_cli_upload_batch(self, mock_post):
        """Test batch upload through CLI."""
        # Mock successful API response
        batch_response = {
            "success": True,
            "batch_id": "batch-123",
            "total_files": 2,
            "successful_uploads": 2,
            "failed_uploads": 0
        }
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = batch_response
        
        # Create temporary test files
        temp_files = []
        for i in range(2):
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.pdf', delete=False) as f:
                f.write(f"Test PDF content {i}")
                temp_files.append(f.name)
        
        try:
            result = self.cli_obj.upload_batch(
                file_paths=temp_files,
                description="Batch test",
                priority=5
            )
            
            assert result["success"] is True
            assert result["batch_id"] == "batch-123"
            assert result["total_files"] == 2
            
        finally:
            for temp_file in temp_files:
                Path(temp_file).unlink(missing_ok=True)
    
    @patch('requests.Session.get')
    def test_cli_get_batch_status(self, mock_get):
        """Test getting batch status through CLI."""
        # Mock API response
        batch_status = {
            "batch_id": "batch-123",
            "status": "processing",
            "total_documents": 5,
            "processed_documents": 3,
            "failed_documents": 0,
            "progress_percentage": 60.0
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = batch_status
        
        result = self.cli_obj.get_batch_status("batch-123")
        
        assert result == batch_status
        assert result["progress_percentage"] == 60.0
    
    @patch('requests.Session.get')
    def test_cli_download_report(self, mock_get):
        """Test downloading report through CLI."""
        # Mock API response
        mock_report_content = b"PDF report content"
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = mock_report_content
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            output_path = f.name
        
        try:
            result = self.cli_obj.download_report("test-doc-123", output_path, "pdf")
            
            assert result is True
            
            # Verify file was written
            with open(output_path, 'rb') as f:
                content = f.read()
                assert content == mock_report_content
                
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    @patch('requests.Session.get')
    @patch('time.sleep')
    def test_cli_wait_for_completion(self, mock_sleep, mock_get):
        """Test waiting for analysis completion."""
        # Mock status responses: processing -> completed
        status_responses = [
            Mock(status_code=200, json=lambda: {"status": "processing"}),
            Mock(status_code=200, json=lambda: {"status": "completed"}),
            Mock(status_code=200, json=lambda: self.mock_analysis_results)
        ]
        
        mock_get.side_effect = status_responses
        
        result = self.cli_obj.wait_for_completion("test-doc-123", timeout=10)
        
        assert result == self.mock_analysis_results
        assert mock_get.call_count == 3  # 2 status checks + 1 results fetch


class TestCLICommands:
    """Test CLI commands using Click's test runner."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('src.document_forensics.cli.main.DocumentForensicsCLI')
    def test_analyze_command_success(self, mock_cli_class):
        """Test the analyze command with successful execution."""
        # Mock CLI instance
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        # Mock successful upload and analysis
        mock_cli.upload_document.return_value = {"success": True, "document_id": "test-123"}
        mock_cli.start_analysis.return_value = True
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
            f.write("Test content")
            temp_path = f.name
        
        try:
            result = self.runner.invoke(cli, [
                'analyze', temp_path,
                '--description', 'Test document',
                '--tags', 'test',
                '--priority', '7'
            ])
            
            assert result.exit_code == 0
            assert "Document uploaded successfully" in result.output
            assert "Analysis started" in result.output
            
            # Verify CLI methods were called
            mock_cli.upload_document.assert_called_once()
            mock_cli.start_analysis.assert_called_once_with("test-123")
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @patch('src.document_forensics.cli.main.DocumentForensicsCLI')
    def test_analyze_command_with_wait(self, mock_cli_class):
        """Test the analyze command with wait option."""
        # Mock CLI instance
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        # Mock successful workflow
        mock_cli.upload_document.return_value = {"success": True, "document_id": "test-123"}
        mock_cli.start_analysis.return_value = True
        mock_cli.wait_for_completion.return_value = {
            "document_id": "test-123",
            "overall_risk_assessment": "low",
            "confidence_score": 0.9
        }
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
            f.write("Test content")
            temp_path = f.name
        
        try:
            result = self.runner.invoke(cli, [
                'analyze', temp_path, '--wait'
            ])
            
            assert result.exit_code == 0
            assert "ANALYSIS RESULTS" in result.output
            
            # Verify wait_for_completion was called
            mock_cli.wait_for_completion.assert_called_once()
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @patch('src.document_forensics.cli.main.DocumentForensicsCLI')
    def test_status_command(self, mock_cli_class):
        """Test the status command."""
        # Mock CLI instance
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        # Mock status response
        mock_cli.get_document_status.return_value = {
            "status": "completed"
        }
        
        result = self.runner.invoke(cli, ['status', 'test-doc-123'])
        
        assert result.exit_code == 0
        assert "Status: COMPLETED" in result.output
        mock_cli.get_document_status.assert_called_once_with('test-doc-123')
    
    @patch('src.document_forensics.cli.main.DocumentForensicsCLI')
    def test_results_command(self, mock_cli_class):
        """Test the results command."""
        # Mock CLI instance
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        # Mock analysis results
        mock_results = {
            "document_id": "test-123",
            "overall_risk_assessment": "medium",
            "confidence_score": 0.75
        }
        mock_cli.get_analysis_results.return_value = mock_results
        
        result = self.runner.invoke(cli, ['results', 'test-doc-123'])
        
        assert result.exit_code == 0
        assert "ANALYSIS RESULTS" in result.output
        assert "MEDIUM" in result.output
        mock_cli.get_analysis_results.assert_called_once_with('test-doc-123')
    
    @patch('src.document_forensics.cli.main.DocumentForensicsCLI')
    def test_batch_command(self, mock_cli_class):
        """Test the batch command."""
        # Mock CLI instance
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        # Mock batch upload response
        mock_cli.upload_batch.return_value = {
            "success": True,
            "batch_id": "batch-123"
        }
        
        # Create temporary directory with test files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            for i in range(3):
                test_file = temp_path / f"test{i}.pdf"
                test_file.write_text(f"Test content {i}")
            
            result = self.runner.invoke(cli, [
                'batch', str(temp_path),
                '--pattern', '*.pdf',
                '--description', 'Test batch'
            ])
            
            assert result.exit_code == 0
            assert "Found 3 files to process" in result.output
            assert "Batch uploaded successfully" in result.output
            mock_cli.upload_batch.assert_called_once()
    
    @patch('src.document_forensics.cli.main.DocumentForensicsCLI')
    def test_batch_status_command(self, mock_cli_class):
        """Test the batch-status command."""
        # Mock CLI instance
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        # Mock batch status
        mock_cli.get_batch_status.return_value = {
            "batch_id": "batch-123",
            "status": "completed",
            "total_documents": 5,
            "processed_documents": 5,
            "failed_documents": 0,
            "progress_percentage": 100.0
        }
        
        result = self.runner.invoke(cli, ['batch-status', 'batch-123'])
        
        assert result.exit_code == 0
        assert "BATCH STATUS" in result.output
        assert "COMPLETED" in result.output
        mock_cli.get_batch_status.assert_called_once_with('batch-123')
    
    @patch('src.document_forensics.cli.main.DocumentForensicsCLI')
    def test_download_command(self, mock_cli_class):
        """Test the download command."""
        # Mock CLI instance
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        # Mock successful download
        mock_cli.download_report.return_value = True
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            output_path = f.name
        
        try:
            result = self.runner.invoke(cli, [
                'download', 'test-doc-123', output_path, '--format', 'pdf'
            ])
            
            assert result.exit_code == 0
            assert "Report downloaded to" in result.output
            mock_cli.download_report.assert_called_once_with('test-doc-123', output_path, 'pdf')
            
        finally:
            Path(output_path).unlink(missing_ok=True)


class TestCLIDisplayFunctions:
    """Test CLI display and formatting functions."""
    
    def test_display_analysis_results(self, capsys):
        """Test analysis results display formatting."""
        mock_results = {
            "document_id": "test-123",
            "overall_risk_assessment": "high",
            "confidence_score": 0.85,
            "processing_time": 2.5,
            "tampering_analysis": {
                "overall_risk": "high",
                "detected_modifications": [
                    {"description": "Text modification detected", "confidence": 0.8},
                    {"description": "Image manipulation found", "confidence": 0.9}
                ]
            },
            "authenticity_analysis": {
                "authenticity_score": {
                    "overall_score": 0.6,
                    "confidence_level": 0.7
                }
            },
            "visual_evidence": [
                {"type": "tampering_heatmap", "description": "Heatmap analysis"},
                {"type": "pixel_analysis", "description": "Pixel inconsistencies"}
            ]
        }
        
        display_analysis_results(mock_results)
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "ANALYSIS RESULTS" in output
        assert "HIGH" in output
        assert "85.0%" in output
        assert "TAMPERING ANALYSIS" in output
        assert "2 potential modifications detected" in output
        assert "AUTHENTICITY ANALYSIS" in output
        assert "60.0%" in output
        assert "VISUAL EVIDENCE" in output
    
    def test_display_batch_summary(self, capsys):
        """Test batch summary display formatting."""
        batch_status = {
            "batch_id": "batch-123",
            "status": "completed",
            "total_documents": 10,
            "processed_documents": 9,
            "failed_documents": 1,
            "progress_percentage": 100.0
        }
        
        display_batch_summary(batch_status)
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "BATCH STATUS" in output
        assert "COMPLETED" in output
        assert "100.0%" in output
        assert "10" in output  # total documents
        assert "9" in output   # processed documents
        assert "1" in output   # failed documents


class TestCLIErrorHandling:
    """Test CLI error handling scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('src.document_forensics.cli.main.DocumentForensicsCLI')
    def test_analyze_upload_failure(self, mock_cli_class):
        """Test analyze command with upload failure."""
        # Mock CLI instance
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        # Mock failed upload
        mock_cli.upload_document.return_value = {
            "success": False,
            "error": "Invalid file format"
        }
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.invalid', delete=False) as f:
            f.write("Invalid content")
            temp_path = f.name
        
        try:
            result = self.runner.invoke(cli, ['analyze', temp_path])
            
            assert result.exit_code == 1
            assert "Upload failed" in result.output
            assert "Invalid file format" in result.output
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @patch('src.document_forensics.cli.main.DocumentForensicsCLI')
    def test_status_document_not_found(self, mock_cli_class):
        """Test status command with non-existent document."""
        # Mock CLI instance
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        # Mock document not found
        mock_cli.get_document_status.return_value = None
        
        result = self.runner.invoke(cli, ['status', 'nonexistent-doc'])
        
        assert result.exit_code == 1
        assert "Document not found" in result.output
    
    @patch('src.document_forensics.cli.main.DocumentForensicsCLI')
    def test_results_no_results(self, mock_cli_class):
        """Test results command with no results available."""
        # Mock CLI instance
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        # Mock no results
        mock_cli.get_analysis_results.return_value = None
        
        result = self.runner.invoke(cli, ['results', 'test-doc-123'])
        
        assert result.exit_code == 1
        assert "No results found" in result.output
    
    @patch('src.document_forensics.cli.main.DocumentForensicsCLI')
    def test_download_failure(self, mock_cli_class):
        """Test download command with download failure."""
        # Mock CLI instance
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        # Mock failed download
        mock_cli.download_report.return_value = False
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            output_path = f.name
        
        try:
            result = self.runner.invoke(cli, [
                'download', 'test-doc-123', output_path
            ])
            
            assert result.exit_code == 1
            assert "Failed to download report" in result.output
            
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    def test_batch_no_files_found(self):
        """Test batch command with no matching files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(cli, [
                'batch', temp_dir, '--pattern', '*.nonexistent'
            ])
            
            assert result.exit_code == 1
            assert "No files found matching pattern" in result.output


class TestCLINetworkHandling:
    """Test CLI network error handling."""
    
    @patch('requests.Session.post')
    def test_network_error_handling(self, mock_post):
        """Test handling of network errors in CLI."""
        # Mock network error
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")
        
        cli_obj = DocumentForensicsCLI()
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
            f.write("Test content")
            temp_path = f.name
        
        try:
            result = cli_obj.upload_document(temp_path)
            
            assert result["success"] is False
            assert "Upload error" in result["error"]
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @patch('requests.Session.get')
    def test_timeout_handling(self, mock_get):
        """Test handling of request timeouts in CLI."""
        # Mock timeout
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")
        
        cli_obj = DocumentForensicsCLI()
        result = cli_obj.get_document_status("test-doc-123")
        
        assert result is None
    
    @patch('requests.Session.get')
    def test_http_error_handling(self, mock_get):
        """Test handling of HTTP errors in CLI."""
        # Mock HTTP error
        mock_get.return_value.status_code = 500
        mock_get.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError("Server error")
        
        cli_obj = DocumentForensicsCLI()
        result = cli_obj.get_analysis_results("test-doc-123")
        
        assert result is None


@pytest.fixture
def temp_batch_files():
    """Create temporary files for batch testing."""
    temp_files = []
    temp_dir = tempfile.mkdtemp()
    
    for i in range(3):
        file_path = Path(temp_dir) / f"test{i}.pdf"
        file_path.write_text(f"Test content {i}")
        temp_files.append(str(file_path))
    
    yield temp_files, temp_dir
    
    # Cleanup
    for file_path in temp_files:
        Path(file_path).unlink(missing_ok=True)
    Path(temp_dir).rmdir()


class TestCLIBatchOperations:
    """Test CLI batch operations."""
    
    @patch('requests.Session.post')
    def test_batch_upload_success(self, mock_post, temp_batch_files):
        """Test successful batch upload."""
        temp_files, temp_dir = temp_batch_files
        
        # Mock successful batch response
        batch_response = {
            "success": True,
            "batch_id": "batch-123",
            "total_files": 3,
            "successful_uploads": 3,
            "failed_uploads": 0
        }
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = batch_response
        
        cli_obj = DocumentForensicsCLI()
        result = cli_obj.upload_batch(temp_files)
        
        assert result["success"] is True
        assert result["batch_id"] == "batch-123"
        assert result["total_files"] == 3
    
    def test_batch_file_discovery(self, temp_batch_files):
        """Test file discovery for batch operations."""
        temp_files, temp_dir = temp_batch_files
        
        # Test glob pattern matching
        directory_path = Path(temp_dir)
        found_files = list(directory_path.glob("*.pdf"))
        
        assert len(found_files) == 3
        for file_path in found_files:
            assert file_path.suffix == ".pdf"
            assert file_path.exists()


class TestCLIProgressTracking:
    """Test CLI progress tracking functionality."""
    
    @patch('requests.Session.get')
    @patch('time.sleep')
    def test_progress_tracking_workflow(self, mock_sleep, mock_get):
        """Test progress tracking during analysis."""
        # Mock progressive status updates
        status_sequence = [
            {"status": "pending"},
            {"status": "processing"},
            {"status": "processing"},
            {"status": "completed"}
        ]
        
        # Mock final results
        final_results = {
            "document_id": "test-123",
            "overall_risk_assessment": "low",
            "confidence_score": 0.9
        }
        
        # Set up mock responses
        mock_responses = []
        for status in status_sequence:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = status
            mock_responses.append(mock_response)
        
        # Add final results response
        final_response = Mock()
        final_response.status_code = 200
        final_response.json.return_value = final_results
        mock_responses.append(final_response)
        
        mock_get.side_effect = mock_responses
        
        cli_obj = DocumentForensicsCLI()
        result = cli_obj.wait_for_completion("test-123", timeout=30)
        
        assert result == final_results
        assert mock_get.call_count == 5  # 4 status checks + 1 results fetch
        assert mock_sleep.call_count == 3  # Sleep between status checks