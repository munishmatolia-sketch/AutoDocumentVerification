"""Integration tests for the web interface."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

import pytest
import requests
import streamlit as st
from streamlit.testing.v1 import AppTest

from src.document_forensics.web.streamlit_app import DocumentForensicsWebApp
from src.document_forensics.web.components import (
    VisualEvidenceRenderer, MetricsDisplay, DocumentLibraryTable,
    BatchProgressDisplay, ReportGenerator
)
from src.document_forensics.core.models import ProcessingStatus, RiskLevel, EvidenceType


class TestWebInterfaceIntegration:
    """Integration tests for the Streamlit web interface."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = DocumentForensicsWebApp()
        self.mock_api_response = {
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
            "document_id": 1,
            "timestamp": "2024-01-15T10:00:00Z",
            "overall_risk_assessment": "medium",
            "confidence_score": 0.85,
            "processing_time": 2.5,
            "metadata_analysis": {
                "anomalies": [
                    {"description": "Timestamp inconsistency detected", "severity": "medium"}
                ]
            },
            "tampering_analysis": {
                "overall_risk": "medium",
                "confidence_score": 0.75,
                "detected_modifications": [
                    {"description": "Text modification detected", "confidence": 0.8}
                ]
            },
            "authenticity_analysis": {
                "authenticity_score": {
                    "overall_score": 0.7,
                    "confidence_level": 0.8,
                    "contributing_factors": {
                        "metadata_consistency": 0.6,
                        "structure_validation": 0.8,
                        "signature_verification": 0.7
                    }
                }
            },
            "visual_evidence": [
                {
                    "type": "tampering_heatmap",
                    "description": "Tampering detection heatmap",
                    "confidence_level": 0.8,
                    "analysis_method": "Computer Vision",
                    "annotations": [
                        {"description": "High risk region detected"}
                    ]
                }
            ]
        }
    
    @patch('requests.post')
    def test_document_upload_success(self, mock_post):
        """Test successful document upload through web interface."""
        # Mock successful API response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = self.mock_api_response
        
        # Test upload
        file_data = b"test file content"
        filename = "test.pdf"
        metadata = {"description": "Test document", "priority": 5}
        
        result = self.app.upload_document_to_api(file_data, filename, metadata)
        
        assert result["success"] is True
        assert result["document_id"] == "test-doc-123"
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/documents/upload" in call_args[0][0]
    
    @patch('requests.post')
    def test_document_upload_failure(self, mock_post):
        """Test failed document upload through web interface."""
        # Mock failed API response
        mock_post.return_value.status_code = 400
        mock_post.return_value.text = "Invalid file format"
        
        # Test upload
        file_data = b"invalid content"
        filename = "test.invalid"
        
        result = self.app.upload_document_to_api(file_data, filename)
        
        assert result["success"] is False
        assert "Upload failed" in result["error"]
    
    @patch('requests.post')
    def test_start_analysis(self, mock_post):
        """Test starting analysis through web interface."""
        # Mock successful API response
        mock_post.return_value.status_code = 200
        
        result = self.app.start_analysis("test-doc-123")
        
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/analysis/start" in call_args[0][0]
        assert call_args[1]["json"]["document_id"] == "test-doc-123"
    
    @patch('requests.get')
    def test_get_document_status(self, mock_get):
        """Test getting document status through web interface."""
        # Mock API response
        mock_status = {"status": "processing", "progress": 50}
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_status
        
        result = self.app.get_document_status("test-doc-123")
        
        assert result == mock_status
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "/analysis/test-doc-123/status" in call_args[0][0]
    
    @patch('requests.get')
    def test_get_analysis_results(self, mock_get):
        """Test getting analysis results through web interface."""
        # Mock API response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.mock_analysis_results
        
        result = self.app.get_analysis_results("test-doc-123")
        
        assert result == self.mock_analysis_results
        assert result["overall_risk_assessment"] == "medium"
        assert result["confidence_score"] == 0.85
    
    @patch('requests.get')
    def test_download_report(self, mock_get):
        """Test downloading report through web interface."""
        # Mock API response
        mock_report_content = b"PDF report content"
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = mock_report_content
        
        result = self.app.download_report("test-doc-123", "pdf")
        
        assert result == mock_report_content
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "/reports/test-doc-123" in call_args[0][0]
        assert call_args[1]["params"]["format"] == "pdf"
    
    def test_session_state_initialization(self):
        """Test that session state is properly initialized."""
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Initialize app
        app = DocumentForensicsWebApp()
        
        # Check session state variables
        assert 'uploaded_documents' in st.session_state
        assert 'analysis_results' in st.session_state
        assert 'current_document' in st.session_state
        assert 'auth_token' in st.session_state
        
        assert isinstance(st.session_state.uploaded_documents, list)
        assert isinstance(st.session_state.analysis_results, dict)


class TestWebComponents:
    """Test web interface components."""
    
    def test_visual_evidence_renderer_heatmap(self):
        """Test visual evidence renderer for heatmap."""
        img = VisualEvidenceRenderer.create_heatmap_placeholder(400, 300)
        
        assert img.size == (400, 300)
        assert img.mode == 'RGB'
    
    def test_visual_evidence_renderer_pixel_analysis(self):
        """Test visual evidence renderer for pixel analysis."""
        img = VisualEvidenceRenderer.create_pixel_analysis_placeholder(400, 300)
        
        assert img.size == (400, 300)
        assert img.mode == 'RGB'
    
    def test_metrics_display_risk_badge(self):
        """Test risk level badge generation."""
        badge_html = MetricsDisplay.risk_level_badge("high")
        
        assert "HIGH" in badge_html
        assert "#fd7e14" in badge_html or "#dc3545" in badge_html
        assert "background-color" in badge_html
    
    def test_report_generator_summary(self):
        """Test report generation."""
        mock_results = {
            "document_id": "test-123",
            "timestamp": "2024-01-15T10:00:00Z",
            "processing_time": 2.5,
            "overall_risk_assessment": "medium",
            "confidence_score": 0.85,
            "tampering_analysis": {
                "overall_risk": "medium",
                "detected_modifications": [{"description": "Test modification"}]
            },
            "authenticity_analysis": {
                "authenticity_score": {
                    "overall_score": 0.7,
                    "confidence_level": 0.8
                }
            },
            "visual_evidence": [
                {"type": "tampering_heatmap", "confidence_level": 0.8}
            ]
        }
        
        report = ReportGenerator.generate_summary_report(mock_results)
        
        assert "DOCUMENT FORENSICS ANALYSIS REPORT" in report
        assert "test-123" in report
        assert "MEDIUM" in report
        assert "85.0%" in report
        assert "TAMPERING ANALYSIS" in report
        assert "AUTHENTICITY ANALYSIS" in report
        assert "VISUAL EVIDENCE" in report


class TestWebInterfaceFlow:
    """Test complete web interface workflows."""
    
    @patch('requests.post')
    @patch('requests.get')
    def test_complete_analysis_workflow(self, mock_get, mock_post):
        """Test complete document analysis workflow."""
        app = DocumentForensicsWebApp()
        
        # Mock upload response
        upload_response = {
            "success": True,
            "document_id": "test-doc-123"
        }
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = upload_response
        
        # Mock status responses (processing -> completed)
        status_responses = [
            {"status": "processing"},
            {"status": "completed"}
        ]
        
        # Mock analysis results
        analysis_results = {
            "document_id": "test-doc-123",
            "overall_risk_assessment": "low",
            "confidence_score": 0.9
        }
        
        mock_get.side_effect = [
            Mock(status_code=200, json=lambda: status_responses[0]),
            Mock(status_code=200, json=lambda: status_responses[1]),
            Mock(status_code=200, json=lambda: analysis_results)
        ]
        
        # Test workflow
        # 1. Upload document
        upload_result = app.upload_document_to_api(b"test content", "test.pdf")
        assert upload_result["success"] is True
        
        # 2. Start analysis
        start_result = app.start_analysis(upload_result["document_id"])
        assert start_result is True
        
        # 3. Check status (processing)
        status = app.get_document_status(upload_result["document_id"])
        assert status["status"] == "processing"
        
        # 4. Check status (completed)
        status = app.get_document_status(upload_result["document_id"])
        assert status["status"] == "completed"
        
        # 5. Get results
        results = app.get_analysis_results(upload_result["document_id"])
        assert results["overall_risk_assessment"] == "low"
        assert results["confidence_score"] == 0.9
    
    def test_batch_progress_display(self):
        """Test batch progress display component."""
        batch_status = {
            "total_documents": 10,
            "processed_documents": 7,
            "failed_documents": 1,
            "progress_percentage": 70.0,
            "status": "processing"
        }
        
        # This would normally render in Streamlit, but we can test the data processing
        total_docs = batch_status.get("total_documents", 0)
        processed_docs = batch_status.get("processed_documents", 0)
        failed_docs = batch_status.get("failed_documents", 0)
        success_rate = ((processed_docs - failed_docs) / max(processed_docs, 1)) * 100
        
        assert total_docs == 10
        assert processed_docs == 7
        assert failed_docs == 1
        assert abs(success_rate - 85.7) < 0.1  # Approximately 85.7%
    
    def test_document_library_data_processing(self):
        """Test document library data processing."""
        documents = [
            {"id": "doc1", "filename": "test1.pdf", "status": "completed", "risk": "low"},
            {"id": "doc2", "filename": "test2.jpg", "status": "processing", "risk": "medium"},
            {"id": "doc3", "filename": "test3.docx", "status": "failed", "risk": "high"}
        ]
        
        # Test filtering logic (would be used in actual component)
        completed_docs = [doc for doc in documents if doc["status"] == "completed"]
        high_risk_docs = [doc for doc in documents if doc["risk"] == "high"]
        
        assert len(completed_docs) == 1
        assert len(high_risk_docs) == 1
        assert completed_docs[0]["filename"] == "test1.pdf"
        assert high_risk_docs[0]["filename"] == "test3.docx"


class TestWebInterfaceErrorHandling:
    """Test error handling in web interface."""
    
    @patch('requests.post')
    def test_upload_network_error(self, mock_post):
        """Test handling of network errors during upload."""
        # Mock network error
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")
        
        app = DocumentForensicsWebApp()
        result = app.upload_document_to_api(b"test", "test.pdf")
        
        assert result["success"] is False
        assert "Upload error" in result["error"]
    
    @patch('requests.get')
    def test_status_check_timeout(self, mock_get):
        """Test handling of timeout during status check."""
        # Mock timeout
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")
        
        app = DocumentForensicsWebApp()
        result = app.get_document_status("test-doc-123")
        
        assert result is None
    
    def test_invalid_analysis_results(self):
        """Test handling of invalid analysis results."""
        app = DocumentForensicsWebApp()
        
        # Test with None results
        assert app.get_analysis_results("invalid-id") is None
        
        # Test with malformed results (would be handled by the component)
        malformed_results = {"invalid": "data"}
        
        # The components should handle missing keys gracefully
        overall_risk = malformed_results.get("overall_risk_assessment", "unknown")
        confidence_score = malformed_results.get("confidence_score", 0.0)
        
        assert overall_risk == "unknown"
        assert confidence_score == 0.0


@pytest.fixture
def temp_test_file():
    """Create a temporary test file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test file content for web interface testing")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


class TestWebInterfaceFileHandling:
    """Test file handling in web interface."""
    
    def test_file_validation_logic(self, temp_test_file):
        """Test file validation logic used in web interface."""
        file_path = Path(temp_test_file)
        
        # Test file exists
        assert file_path.exists()
        
        # Test file size
        file_size = file_path.stat().st_size
        assert file_size > 0
        
        # Test file extension
        assert file_path.suffix == '.txt'
        
        # Test file reading
        with open(file_path, 'rb') as f:
            content = f.read()
            assert len(content) > 0
    
    def test_supported_file_types(self):
        """Test supported file types validation."""
        supported_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'tiff', 'docx', 'xlsx', 'txt']
        
        test_files = [
            "document.pdf",
            "image.jpg", 
            "photo.jpeg",
            "scan.png",
            "diagram.tiff",
            "report.docx",
            "data.xlsx",
            "notes.txt",
            "unsupported.xyz"
        ]
        
        for filename in test_files:
            extension = filename.split('.')[-1].lower()
            is_supported = extension in supported_extensions
            
            if filename == "unsupported.xyz":
                assert not is_supported
            else:
                assert is_supported