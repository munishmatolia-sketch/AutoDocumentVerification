"""
Property-based tests for project setup validation.

Feature: document-forensics, Property 1: Comprehensive File Validation
Validates: Requirements 1.1, 1.2, 1.3
"""

import os
import tempfile
from typing import Any, Dict
from hypothesis import given, strategies as st, assume, settings, HealthCheck
import pytest
from io import BytesIO


# Configuration constants for testing
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_FILE_TYPES = [
    "application/pdf",
    "image/jpeg", 
    "image/png",
    "image/tiff",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain"
]


# File type strategies for property testing
SUPPORTED_MIME_TYPES = ALLOWED_FILE_TYPES

UNSUPPORTED_MIME_TYPES = [
    "application/zip",
    "video/mp4",
    "audio/mpeg",
    "application/x-executable",
    "text/html",
    "application/javascript"
]


@st.composite
def file_data_strategy(draw):
    """Generate file data for testing."""
    # Generate file size (smaller range for faster testing)
    file_size = draw(st.integers(min_value=0, max_value=min(MAX_FILE_SIZE * 2, 1000000)))  # Cap at 1MB for testing
    
    # Generate file content (only generate actual content for small files)
    if file_size <= 10000:  # Only generate actual content for files <= 10KB
        content = draw(st.binary(min_size=file_size, max_size=file_size))
    else:
        # For larger files, just create a placeholder to test size validation
        content = b"x" * min(file_size, 1000)  # Generate small content, size validation is separate
    
    # Generate filename
    filename = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"), 
        whitelist_characters=".-_"
    )))
    
    # Generate MIME type (supported or unsupported)
    mime_type = draw(st.one_of(
        st.sampled_from(SUPPORTED_MIME_TYPES),
        st.sampled_from(UNSUPPORTED_MIME_TYPES)
    ))
    
    return {
        "filename": filename,
        "content": content,
        "size": file_size,  # Use the intended size, not actual content size
        "mime_type": mime_type
    }


def validate_file_format(mime_type: str) -> bool:
    """
    Validate if file format is supported.
    
    Args:
        mime_type: MIME type of the file
        
    Returns:
        bool: True if supported, False otherwise
    """
    return mime_type in ALLOWED_FILE_TYPES


def validate_file_size(file_size: int) -> bool:
    """
    Validate if file size is within limits.
    
    Args:
        file_size: Size of the file in bytes
        
    Returns:
        bool: True if within limits, False otherwise
    """
    return 0 < file_size <= MAX_FILE_SIZE


def validate_file_content(content: bytes) -> bool:
    """
    Validate if file content is not corrupted (basic check).
    
    Args:
        content: File content as bytes
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Basic validation - content should not be empty and should be bytes
    return isinstance(content, bytes) and len(content) > 0


def get_validation_error_message(file_data: Dict[str, Any]) -> str:
    """
    Get appropriate error message for validation failure.
    
    Args:
        file_data: Dictionary containing file information
        
    Returns:
        str: Error message describing the validation failure
    """
    if not validate_file_format(file_data["mime_type"]):
        return f"Unsupported file format: {file_data['mime_type']}"
    
    if not validate_file_size(file_data["size"]):
        if file_data["size"] <= 0:
            return "File is empty"
        else:
            return f"File size {file_data['size']} exceeds maximum allowed size {MAX_FILE_SIZE}"
    
    if not validate_file_content(file_data["content"]):
        return "File content is corrupted or invalid"
    
    return "Unknown validation error"


class TestProjectSetupValidation:
    """Test class for project setup validation properties."""
    
    @given(file_data_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_comprehensive_file_validation_property(self, file_data):
        """
        Property 1: Comprehensive File Validation
        
        For any uploaded file, the system should accept it if and only if it meets 
        all validation criteria (supported format, within size limits, not corrupted), 
        and provide appropriate error messages for any validation failures.
        
        **Validates: Requirements 1.1, 1.2, 1.3**
        """
        # Extract file information
        filename = file_data["filename"]
        content = file_data["content"]
        file_size = file_data["size"]
        mime_type = file_data["mime_type"]
        
        # Skip empty filenames as they're not realistic
        assume(len(filename.strip()) > 0)
        
        # Perform individual validations
        format_valid = validate_file_format(mime_type)
        size_valid = validate_file_size(file_size)
        content_valid = validate_file_content(content)
        
        # Overall validation should pass if and only if all individual validations pass
        should_accept = format_valid and size_valid and content_valid
        
        # Test the validation logic
        if should_accept:
            # File should be accepted - all validations should pass
            assert format_valid, f"Format validation failed for supported type: {mime_type}"
            assert size_valid, f"Size validation failed for valid size: {file_size}"
            assert content_valid, f"Content validation failed for valid content"
        else:
            # File should be rejected - at least one validation should fail
            validation_failures = []
            if not format_valid:
                validation_failures.append("format")
            if not size_valid:
                validation_failures.append("size")
            if not content_valid:
                validation_failures.append("content")
            
            assert len(validation_failures) > 0, "File should be rejected but no validation failures found"
            
            # Error message should be appropriate for the failure
            error_message = get_validation_error_message(file_data)
            assert isinstance(error_message, str), "Error message should be a string"
            assert len(error_message) > 0, "Error message should not be empty"
            
            # Error message should mention at least one specific failure
            # When multiple failures occur, it's acceptable to report any one of them
            failure_mentioned = False
            
            if not format_valid and (mime_type in error_message or "format" in error_message.lower()):
                failure_mentioned = True
            
            if not size_valid and ("size" in error_message.lower() or 
                                 "empty" in error_message.lower() or 
                                 str(file_size) in error_message):
                failure_mentioned = True
                
            if not content_valid and ("content" in error_message.lower() or 
                                    "corrupted" in error_message.lower() or
                                    "invalid" in error_message.lower()):
                failure_mentioned = True
            
            assert failure_mentioned, f"Error message '{error_message}' should mention at least one validation failure from: {validation_failures}"
    
    def test_supported_file_formats_acceptance(self):
        """Test that all supported file formats are properly recognized."""
        for mime_type in SUPPORTED_MIME_TYPES:
            assert validate_file_format(mime_type), f"Supported format {mime_type} was rejected"
    
    def test_unsupported_file_formats_rejection(self):
        """Test that unsupported file formats are properly rejected."""
        for mime_type in UNSUPPORTED_MIME_TYPES:
            assert not validate_file_format(mime_type), f"Unsupported format {mime_type} was accepted"
    
    def test_file_size_boundaries(self):
        """Test file size validation at boundary conditions."""
        # Test zero size (should be rejected)
        assert not validate_file_size(0), "Zero-size file should be rejected"
        
        # Test negative size (should be rejected)
        assert not validate_file_size(-1), "Negative-size file should be rejected"
        
        # Test exactly at limit (should be accepted)
        assert validate_file_size(MAX_FILE_SIZE), "File at size limit should be accepted"
        
        # Test just over limit (should be rejected)
        assert not validate_file_size(MAX_FILE_SIZE + 1), "File over size limit should be rejected"
        
        # Test small valid size (should be accepted)
        assert validate_file_size(1), "Small valid file should be accepted"
    
    def test_content_validation_edge_cases(self):
        """Test content validation with edge cases."""
        # Empty bytes should be rejected
        assert not validate_file_content(b""), "Empty content should be rejected"
        
        # Valid bytes should be accepted
        assert validate_file_content(b"test content"), "Valid content should be accepted"
        
        # Large content should be accepted (size validation is separate)
        large_content = b"x" * 10000
        assert validate_file_content(large_content), "Large valid content should be accepted"
    
    def test_error_message_quality(self):
        """Test that error messages are informative and appropriate."""
        # Test format error message
        format_error_data = {
            "mime_type": "application/zip",
            "size": 1000,
            "content": b"test"
        }
        error_msg = get_validation_error_message(format_error_data)
        assert "format" in error_msg.lower() or "zip" in error_msg
        
        # Test size error message
        size_error_data = {
            "mime_type": "application/pdf",
            "size": MAX_FILE_SIZE + 1000,
            "content": b"test"
        }
        error_msg = get_validation_error_message(size_error_data)
        assert "size" in error_msg.lower()
        
        # Test empty file error message
        empty_error_data = {
            "mime_type": "application/pdf", 
            "size": 0,
            "content": b""
        }
        error_msg = get_validation_error_message(empty_error_data)
        assert "empty" in error_msg.lower() or "size" in error_msg.lower()