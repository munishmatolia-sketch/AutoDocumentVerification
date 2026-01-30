"""Data validation functions for document forensics models."""

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None

import mimetypes
from pathlib import Path
from typing import List, Optional, Tuple, Union, Dict, Any
from pydantic import ValidationError

from .models import (
    Document, DocumentMetadata, UploadMetadata, ValidationResult,
    FileType, ProcessingStatus, AnalysisResults, MetadataAnalysis,
    TamperingAnalysis, AuthenticityAnalysis, BatchStatus
)
from ..utils.crypto import DocumentHasher


class DocumentValidator:
    """Validator for document-related data and files."""
    
    # Maximum file sizes by type (in bytes)
    MAX_FILE_SIZES = {
        FileType.PDF: 100 * 1024 * 1024,      # 100MB
        FileType.IMAGE: 50 * 1024 * 1024,     # 50MB
        FileType.DOCX: 25 * 1024 * 1024,      # 25MB
        FileType.XLSX: 25 * 1024 * 1024,      # 25MB
        FileType.TXT: 10 * 1024 * 1024,       # 10MB
    }
    
    # Supported MIME types for each file type
    SUPPORTED_MIME_TYPES = {
        FileType.PDF: ['application/pdf'],
        FileType.IMAGE: [
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
            'image/bmp', 'image/tiff', 'image/webp'
        ],
        FileType.DOCX: [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ],
        FileType.XLSX: [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ],
        FileType.TXT: ['text/plain', 'text/csv']
    }
    
    @classmethod
    def validate_file_content(cls, content: bytes, filename: str) -> ValidationResult:
        """
        Validate file content and determine file type.
        
        Args:
            content: File content as bytes
            filename: Original filename
            
        Returns:
            ValidationResult with validation status and details
        """
        errors = []
        warnings = []
        
        # Check if content is empty
        if not content:
            errors.append("File content is empty")
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings
            )
        
        # Detect MIME type using python-magic if available
        detected_mime = None
        if MAGIC_AVAILABLE:
            try:
                detected_mime = magic.from_buffer(content, mime=True)
            except Exception as e:
                warnings.append(f"Failed to detect file type with magic: {str(e)}")
        
        # Fallback to filename extension
        if not detected_mime:
            detected_mime, _ = mimetypes.guess_type(filename)
            if detected_mime:
                warnings.append("File type detected from filename extension (magic library not available)")
        
        if not detected_mime:
            errors.append("Could not determine file type")
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings
            )
        
        # Determine FileType from MIME type
        file_type = None
        for ft, mime_types in cls.SUPPORTED_MIME_TYPES.items():
            if detected_mime in mime_types:
                file_type = ft
                break
        
        if not file_type:
            errors.append(f"Unsupported file type: {detected_mime}")
            return ValidationResult(
                is_valid=False,
                detected_format=detected_mime,
                errors=errors,
                warnings=warnings
            )
        
        # Check file size limits
        file_size = len(content)
        max_size = cls.MAX_FILE_SIZES.get(file_type, 10 * 1024 * 1024)
        
        if file_size > max_size:
            errors.append(f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)")
        
        # Additional format-specific validation
        format_errors = cls._validate_format_specific(content, file_type, detected_mime)
        errors.extend(format_errors)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            file_type=file_type,
            detected_format=detected_mime,
            size=file_size,
            errors=errors,
            warnings=warnings
        )
    
    @classmethod
    def _validate_format_specific(cls, content: bytes, file_type: FileType, 
                                mime_type: str) -> List[str]:
        """
        Perform format-specific validation.
        
        Args:
            content: File content
            file_type: Detected file type
            mime_type: Detected MIME type
            
        Returns:
            List of validation errors
        """
        errors = []
        
        try:
            if file_type == FileType.PDF:
                # Basic PDF validation - check for PDF header
                if not content.startswith(b'%PDF-'):
                    errors.append("Invalid PDF format: missing PDF header")
                
            elif file_type == FileType.IMAGE:
                # Basic image validation - check for common image headers
                image_headers = {
                    b'\xFF\xD8\xFF': 'JPEG',
                    b'\x89PNG\r\n\x1a\n': 'PNG',
                    b'GIF87a': 'GIF87a',
                    b'GIF89a': 'GIF89a',
                    b'BM': 'BMP',
                    b'II*\x00': 'TIFF (little endian)',
                    b'MM\x00*': 'TIFF (big endian)',
                }
                
                valid_header = False
                for header, format_name in image_headers.items():
                    if content.startswith(header):
                        valid_header = True
                        break
                
                if not valid_header:
                    errors.append("Invalid image format: unrecognized image header")
                
            elif file_type == FileType.DOCX:
                # Basic DOCX validation - check for ZIP header (DOCX is a ZIP file)
                if not content.startswith(b'PK'):
                    errors.append("Invalid DOCX format: missing ZIP header")
                
            elif file_type == FileType.XLSX:
                # Basic XLSX validation - check for ZIP header (XLSX is a ZIP file)
                if not content.startswith(b'PK'):
                    errors.append("Invalid XLSX format: missing ZIP header")
                
            elif file_type == FileType.TXT:
                # Basic text validation - try to decode as UTF-8
                try:
                    content.decode('utf-8')
                except UnicodeDecodeError:
                    # Try other common encodings
                    encodings = ['latin-1', 'cp1252', 'iso-8859-1']
                    decoded = False
                    for encoding in encodings:
                        try:
                            content.decode(encoding)
                            decoded = True
                            break
                        except UnicodeDecodeError:
                            continue
                    
                    if not decoded:
                        errors.append("Invalid text format: unable to decode text content")
                        
        except Exception as e:
            errors.append(f"Format validation error: {str(e)}")
        
        return errors
    
    @classmethod
    def validate_document_model(cls, document_data: Dict[str, Any]) -> Tuple[bool, Optional[Document], List[str]]:
        """
        Validate document data against Document model.
        
        Args:
            document_data: Dictionary containing document data
            
        Returns:
            Tuple of (is_valid, document_model, errors)
        """
        try:
            document = Document(**document_data)
            return True, document, []
        except ValidationError as e:
            errors = [f"{error['loc'][0]}: {error['msg']}" for error in e.errors()]
            return False, None, errors
        except Exception as e:
            return False, None, [f"Validation error: {str(e)}"]
    
    @classmethod
    def validate_upload_metadata(cls, metadata_data: Dict[str, Any]) -> Tuple[bool, Optional[UploadMetadata], List[str]]:
        """
        Validate upload metadata against UploadMetadata model.
        
        Args:
            metadata_data: Dictionary containing upload metadata
            
        Returns:
            Tuple of (is_valid, metadata_model, errors)
        """
        try:
            metadata = UploadMetadata(**metadata_data)
            return True, metadata, []
        except ValidationError as e:
            errors = [f"{error['loc'][0]}: {error['msg']}" for error in e.errors()]
            return False, None, errors
        except Exception as e:
            return False, None, [f"Validation error: {str(e)}"]


class AnalysisValidator:
    """Validator for analysis results and related data."""
    
    @classmethod
    def validate_analysis_results(cls, results_data: Dict[str, Any]) -> Tuple[bool, Optional[AnalysisResults], List[str]]:
        """
        Validate analysis results data.
        
        Args:
            results_data: Dictionary containing analysis results
            
        Returns:
            Tuple of (is_valid, results_model, errors)
        """
        try:
            results = AnalysisResults(**results_data)
            return True, results, []
        except ValidationError as e:
            errors = [f"{error['loc'][0]}: {error['msg']}" for error in e.errors()]
            return False, None, errors
        except Exception as e:
            return False, None, [f"Validation error: {str(e)}"]
    
    @classmethod
    def validate_metadata_analysis(cls, analysis_data: Dict[str, Any]) -> Tuple[bool, Optional[MetadataAnalysis], List[str]]:
        """
        Validate metadata analysis data.
        
        Args:
            analysis_data: Dictionary containing metadata analysis data
            
        Returns:
            Tuple of (is_valid, analysis_model, errors)
        """
        try:
            analysis = MetadataAnalysis(**analysis_data)
            return True, analysis, []
        except ValidationError as e:
            errors = [f"{error['loc'][0]}: {error['msg']}" for error in e.errors()]
            return False, None, errors
        except Exception as e:
            return False, None, [f"Validation error: {str(e)}"]
    
    @classmethod
    def validate_tampering_analysis(cls, analysis_data: Dict[str, Any]) -> Tuple[bool, Optional[TamperingAnalysis], List[str]]:
        """
        Validate tampering analysis data.
        
        Args:
            analysis_data: Dictionary containing tampering analysis data
            
        Returns:
            Tuple of (is_valid, analysis_model, errors)
        """
        try:
            analysis = TamperingAnalysis(**analysis_data)
            return True, analysis, []
        except ValidationError as e:
            errors = [f"{error['loc'][0]}: {error['msg']}" for error in e.errors()]
            return False, None, errors
        except Exception as e:
            return False, None, [f"Validation error: {str(e)}"]
    
    @classmethod
    def validate_authenticity_analysis(cls, analysis_data: Dict[str, Any]) -> Tuple[bool, Optional[AuthenticityAnalysis], List[str]]:
        """
        Validate authenticity analysis data.
        
        Args:
            analysis_data: Dictionary containing authenticity analysis data
            
        Returns:
            Tuple of (is_valid, analysis_model, errors)
        """
        try:
            analysis = AuthenticityAnalysis(**analysis_data)
            return True, analysis, []
        except ValidationError as e:
            errors = [f"{error['loc'][0]}: {error['msg']}" for error in e.errors()]
            return False, None, errors
        except Exception as e:
            return False, None, [f"Validation error: {str(e)}"]


class BatchValidator:
    """Validator for batch processing data."""
    
    @classmethod
    def validate_batch_status(cls, status_data: Dict[str, Any]) -> Tuple[bool, Optional[BatchStatus], List[str]]:
        """
        Validate batch status data.
        
        Args:
            status_data: Dictionary containing batch status data
            
        Returns:
            Tuple of (is_valid, status_model, errors)
        """
        try:
            status = BatchStatus(**status_data)
            return True, status, []
        except ValidationError as e:
            errors = [f"{error['loc'][0]}: {error['msg']}" for error in e.errors()]
            return False, None, errors
        except Exception as e:
            return False, None, [f"Validation error: {str(e)}"]
    
    @classmethod
    def validate_batch_consistency(cls, batch_status: BatchStatus) -> List[str]:
        """
        Validate batch status consistency.
        
        Args:
            batch_status: BatchStatus model to validate
            
        Returns:
            List of consistency errors
        """
        errors = []
        
        # Check that processed + failed <= total
        if batch_status.processed_documents + batch_status.failed_documents > batch_status.total_documents:
            errors.append("Sum of processed and failed documents exceeds total documents")
        
        # Check progress percentage consistency
        if batch_status.total_documents > 0:
            expected_progress = (
                (batch_status.processed_documents + batch_status.failed_documents) / 
                batch_status.total_documents * 100
            )
            if abs(batch_status.progress_percentage - expected_progress) > 1.0:
                errors.append(f"Progress percentage ({batch_status.progress_percentage}%) "
                            f"inconsistent with document counts (expected {expected_progress:.1f}%)")
        
        # Check status consistency
        if batch_status.status == ProcessingStatus.COMPLETED:
            if batch_status.processed_documents + batch_status.failed_documents != batch_status.total_documents:
                errors.append("Batch marked as completed but not all documents processed")
        
        return errors


class SecurityValidator:
    """Validator for security-related data and operations."""
    
    @classmethod
    def validate_hash_integrity(cls, content: Union[bytes, str], expected_hash: str) -> bool:
        """
        Validate content integrity using hash comparison.
        
        Args:
            content: Content to validate
            expected_hash: Expected SHA-256 hash
            
        Returns:
            True if hash matches, False otherwise
        """
        return DocumentHasher.verify_hash(content, expected_hash, 'sha256')
    
    @classmethod
    def validate_file_safety(cls, filename: str, content: bytes) -> List[str]:
        """
        Validate file safety (check for potential security issues).
        
        Args:
            filename: Original filename
            content: File content
            
        Returns:
            List of security warnings
        """
        warnings = []
        
        # Check for suspicious filename patterns
        suspicious_patterns = [
            '../', '..\\',  # Path traversal
            '<script', '</script>',  # Script injection
            '<?php', '?>',  # PHP code
            '<%', '%>',  # ASP code
            'javascript:',  # JavaScript protocol
            'data:',  # Data URLs
        ]
        
        filename_lower = filename.lower()
        for pattern in suspicious_patterns:
            if pattern in filename_lower:
                warnings.append(f"Suspicious pattern in filename: {pattern}")
        
        # Check for executable file extensions
        executable_extensions = [
            '.exe', '.bat', '.cmd', '.com', '.scr', '.pif',
            '.vbs', '.js', '.jar', '.app', '.deb', '.rpm'
        ]
        
        file_ext = Path(filename).suffix.lower()
        if file_ext in executable_extensions:
            warnings.append(f"Potentially dangerous file extension: {file_ext}")
        
        # Check content for suspicious patterns
        try:
            # Only check text-based content
            if content.startswith(b'%PDF-') or content.startswith(b'PK'):
                # Skip binary formats
                pass
            else:
                content_str = content.decode('utf-8', errors='ignore').lower()
                script_patterns = ['<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=']
                for pattern in script_patterns:
                    if pattern in content_str:
                        warnings.append(f"Suspicious content pattern: {pattern}")
        except Exception:
            # If we can't decode content, skip content-based checks
            pass
        
        return warnings


# Convenience functions for common validation operations
def validate_document_upload(filename: str, content: bytes, 
                           metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Comprehensive validation for document upload.
    
    Args:
        filename: Original filename
        content: File content
        metadata: Optional upload metadata
        
    Returns:
        Tuple of (is_valid, validation_results)
    """
    results = {
        'file_validation': None,
        'security_warnings': [],
        'metadata_validation': None,
        'document_hash': None,
        'errors': [],
        'warnings': []
    }
    
    # Validate file content and format
    file_validation = DocumentValidator.validate_file_content(content, filename)
    results['file_validation'] = file_validation.dict()
    
    if not file_validation.is_valid:
        results['errors'].extend(file_validation.errors)
        return False, results
    
    # Generate document hash
    try:
        document_hash = DocumentHasher.generate_sha256(content)
        results['document_hash'] = document_hash
    except Exception as e:
        results['errors'].append(f"Failed to generate document hash: {str(e)}")
        return False, results
    
    # Security validation
    security_warnings = SecurityValidator.validate_file_safety(filename, content)
    results['security_warnings'] = security_warnings
    results['warnings'].extend(security_warnings)
    
    # Validate metadata if provided
    if metadata:
        is_valid, _, errors = DocumentValidator.validate_upload_metadata(metadata)
        results['metadata_validation'] = {
            'is_valid': is_valid,
            'errors': errors
        }
        if not is_valid:
            results['errors'].extend(errors)
            return False, results
    
    return True, results


def validate_analysis_completeness(analysis_results: AnalysisResults) -> List[str]:
    """
    Validate that analysis results are complete and consistent.
    
    Args:
        analysis_results: Analysis results to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Check that at least one analysis type is present
    has_analysis = any([
        analysis_results.metadata_analysis,
        analysis_results.tampering_analysis,
        analysis_results.authenticity_analysis
    ])
    
    if not has_analysis:
        errors.append("No analysis results provided")
    
    # Validate confidence scores are reasonable
    if analysis_results.confidence_score < 0.0 or analysis_results.confidence_score > 1.0:
        errors.append("Confidence score must be between 0.0 and 1.0")
    
    # Check processing time is reasonable
    if analysis_results.processing_time and analysis_results.processing_time < 0:
        errors.append("Processing time cannot be negative")
    
    return errors