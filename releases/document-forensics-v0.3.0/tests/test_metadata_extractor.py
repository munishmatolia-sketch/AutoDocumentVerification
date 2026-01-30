"""Property-based tests for metadata extraction functionality.

Feature: document-forensics, Property 3: Comprehensive Metadata Extraction
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
"""

import asyncio
import io
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from PIL import Image
from PyPDF2 import PdfWriter

from src.document_forensics.analysis.metadata_extractor import MetadataExtractor
from src.document_forensics.core.models import MetadataAnalysis, RiskLevel


class TestMetadataExtractorProperties:
    """Property-based tests for metadata extraction."""

    def create_extractor(self):
        """Create a metadata extractor instance."""
        return MetadataExtractor()

    def test_metadata_extractor_initialization(self):
        """Test that metadata extractor initializes correctly."""
        extractor = self.create_extractor()
        assert extractor is not None
        assert hasattr(extractor, 'supported_formats')
        assert 'image' in extractor.supported_formats
        assert 'pdf' in extractor.supported_formats
        assert 'docx' in extractor.supported_formats
        assert 'xlsx' in extractor.supported_formats

    @given(
        width=st.integers(min_value=1, max_value=1000),
        height=st.integers(min_value=1, max_value=1000),
        format_type=st.sampled_from(['PNG', 'JPEG'])
    )
    @settings(max_examples=50, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_image_metadata_extraction_property(self, width, height, format_type):
        """
        Property: For any valid image, metadata extraction should return comprehensive results.
        **Validates: Requirements 2.1, 2.4**
        """
        extractor = self.create_extractor()
        # Generate a test image
        image = Image.new('RGB', (width, height), color='red')
        
        # Save to bytes
        img_bytes = io.BytesIO()
        image.save(img_bytes, format=format_type)
        img_content = img_bytes.getvalue()
        
        # Test the extraction
        filename = f"test_image.{format_type.lower()}"
        
        # Run async function in sync test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                extractor.extract_metadata(filename, img_content)
            )
        finally:
            loop.close()
        
        # Verify the result is a MetadataAnalysis object
        assert isinstance(result, MetadataAnalysis)
        assert isinstance(result.extracted_metadata, dict)
        
        # For valid images, we should have basic metadata
        if 'extraction_error' not in result.extracted_metadata:
            metadata = result.extracted_metadata
            assert 'format' in metadata
            assert 'size' in metadata
            assert metadata['format'] == format_type
            assert metadata['size'] == (width, height)
    @given(
        title=st.text(min_size=1, max_size=100),
        author=st.text(min_size=1, max_size=50)
    )
    @settings(max_examples=30, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_pdf_metadata_extraction_property(self, title, author):
        """
        Property: For any PDF with metadata, extraction should capture document properties.
        **Validates: Requirements 2.2, 2.3**
        """
        extractor = self.create_extractor()
        assume(title.strip() and author.strip())  # Ensure non-empty strings
        
        # Create a simple PDF with metadata
        pdf_writer = PdfWriter()
        pdf_writer.add_blank_page(width=612, height=792)
        
        # Add metadata
        pdf_writer.add_metadata({
            '/Title': title,
            '/Author': author,
            '/Creator': 'Test Creator',
            '/Producer': 'Test Producer'
        })
        
        # Save to bytes
        pdf_bytes = io.BytesIO()
        pdf_writer.write(pdf_bytes)
        pdf_content = pdf_bytes.getvalue()
        
        filename = "test_document.pdf"
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                extractor.extract_metadata(filename, pdf_content)
            )
        finally:
            loop.close()
        
        # Verify the result
        assert isinstance(result, MetadataAnalysis)
        assert isinstance(result.extracted_metadata, dict)
        
        # For valid PDFs, we should have document info
        if 'extraction_error' not in result.extracted_metadata:
            metadata = result.extracted_metadata
            assert 'page_count' in metadata
            assert metadata['page_count'] == 1
            
            if 'document_info' in metadata:
                doc_info = metadata['document_info']
                assert 'Title' in doc_info or 'title' in doc_info
                assert 'Author' in doc_info or 'author' in doc_info

    @given(
        file_extension=st.sampled_from(['.jpg', '.png', '.pdf', '.docx', '.xlsx', '.txt'])
    )
    @settings(max_examples=20, deadline=3000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_unsupported_format_handling_property(self, file_extension):
        """
        Property: For any file format, the extractor should handle it gracefully.
        **Validates: Requirements 2.1, 2.5**
        """
        extractor = self.create_extractor()
        # Create minimal content
        if file_extension == '.txt':
            content = b"Sample text content"
        else:
            content = b"Invalid content for format"
        
        filename = f"test_file{file_extension}"
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                extractor.extract_metadata(filename, content)
            )
        finally:
            loop.close()
        
        # Should always return a MetadataAnalysis object
        assert isinstance(result, MetadataAnalysis)
        assert isinstance(result.extracted_metadata, dict)
        
        # For unsupported formats or invalid content, should have error info
        if file_extension == '.txt':
            assert 'error' in result.extracted_metadata
        elif file_extension in ['.jpg', '.png', '.pdf', '.docx', '.xlsx']:
            # These are supported formats, but invalid content should be handled
            assert 'extraction_error' in result.extracted_metadata or len(result.extracted_metadata) > 0

    def test_software_signature_detection_property(self):
        """
        Property: Software signatures should be detected when present in metadata.
        **Validates: Requirements 2.3, 2.5**
        """
        extractor = self.create_extractor()
        # Test with metadata containing known software signatures
        test_metadata = {
            'creator': 'Adobe Photoshop CS6',
            'producer': 'Microsoft Office Word',
            'exif_detailed': {
                'Image Software': 'GIMP 2.10.0',
                'Image Make': 'Canon'
            }
        }
        
        signatures = extractor._detect_software_signatures(test_metadata)
        
        # Should detect multiple software signatures
        assert len(signatures) > 0
        
        # Check that confidence scores are reasonable
        for signature in signatures:
            assert 0.0 <= signature.confidence <= 1.0
            assert signature.software_name is not None
            assert signature.detection_method is not None

    def test_timestamp_consistency_analysis_property(self):
        """
        Property: Timestamp consistency analysis should identify anomalies.
        **Validates: Requirements 2.2, 2.5**
        """
        extractor = self.create_extractor()
        # Test with inconsistent timestamps
        test_metadata = {
            'creation_date': '2023-01-01T10:00:00',
            'modification_date': '2022-12-31T10:00:00',  # Earlier than creation
            'exif_detailed': {
                'DateTime': '2040-01-01T10:00:00'  # Future date
            }
        }
        
        consistency = extractor._analyze_timestamp_consistency(test_metadata)
        
        if consistency:
            # Should detect inconsistencies
            assert isinstance(consistency.is_consistent, bool)
            assert isinstance(consistency.anomalies, list)
            
            # Future dates should be flagged
            future_anomaly_found = any('future' in anomaly.lower() for anomaly in consistency.anomalies)
            assert future_anomaly_found

    def test_metadata_anomaly_detection_property(self):
        """
        Property: Anomaly detection should identify suspicious patterns.
        **Validates: Requirements 2.5**
        """
        extractor = self.create_extractor()
        # Test with metadata containing extraction errors
        test_metadata_with_error = {'extraction_error': 'Failed to parse file'}
        anomalies = extractor._detect_metadata_anomalies(test_metadata_with_error)
        
        assert len(anomalies) > 0
        error_anomaly = anomalies[0]
        assert error_anomaly.anomaly_type == 'extraction_failure'
        assert error_anomaly.severity == RiskLevel.MEDIUM
        assert error_anomaly.confidence == 1.0

    def test_comprehensive_metadata_extraction_completeness(self):
        """
        Property: Comprehensive extraction should handle all supported formats.
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
        """
        extractor = self.create_extractor()
        # Test that all supported formats are handled
        supported_extensions = []
        for format_type, extensions in extractor.supported_formats.items():
            supported_extensions.extend(extensions)
        
        # Verify we support the required formats from requirements
        required_formats = ['.jpg', '.jpeg', '.png', '.pdf', '.docx', '.xlsx']
        for required_format in required_formats:
            assert required_format in supported_extensions, f"Missing support for {required_format}"
        
        # Test that the extractor has methods for all format types
        assert hasattr(extractor, '_extract_image_metadata')
        assert hasattr(extractor, '_extract_pdf_metadata')
        assert hasattr(extractor, '_extract_docx_metadata')
        assert hasattr(extractor, '_extract_xlsx_metadata')
        
        # Test that analysis methods exist
        assert hasattr(extractor, '_analyze_timestamp_consistency')
        assert hasattr(extractor, '_detect_software_signatures')
        assert hasattr(extractor, '_detect_metadata_anomalies')
        assert hasattr(extractor, '_extract_geo_location')
        assert hasattr(extractor, '_extract_device_fingerprint')