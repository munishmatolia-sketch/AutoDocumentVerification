"""Upload Manager for handling document uploads with validation and security."""

import asyncio
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, BinaryIO
from uuid import UUID, uuid4
from datetime import datetime

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

from ..core.models import (
    Document, 
    FileType, 
    ValidationResult, 
    UploadMetadata, 
    BatchStatus,
    ProcessingStatus
)
from ..core.config import settings
from ..utils.crypto import hash_document
from .progress import ProgressTracker, BatchProgressTracker, ProgressInfo
from .storage import SecureStorage


class FileValidator:
    """Validates uploaded files for format, size, and security."""
    
    def __init__(self):
        """Initialize file validator."""
        if MAGIC_AVAILABLE:
            self.magic_mime = magic.Magic(mime=True)
            self.magic_type = magic.Magic()
        else:
            self.magic_mime = None
            self.magic_type = None
        
        # MIME type to FileType mapping
        self.mime_to_filetype = {
            "application/pdf": FileType.PDF,
            "image/jpeg": FileType.IMAGE,
            "image/png": FileType.IMAGE,
            "image/tiff": FileType.IMAGE,
            "image/bmp": FileType.IMAGE,
            "image/gif": FileType.IMAGE,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.DOCX,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileType.XLSX,
            "text/plain": FileType.TXT,
        }
        
        # File extension to FileType mapping (fallback when magic is not available)
        self.extension_to_filetype = {
            ".pdf": FileType.PDF,
            ".jpg": FileType.IMAGE,
            ".jpeg": FileType.IMAGE,
            ".png": FileType.IMAGE,
            ".tiff": FileType.IMAGE,
            ".tif": FileType.IMAGE,
            ".bmp": FileType.IMAGE,
            ".gif": FileType.IMAGE,
            ".docx": FileType.DOCX,
            ".xlsx": FileType.XLSX,
            ".txt": FileType.TXT,
        }
    
    def validate_file_format(self, file_path: str, original_filename: Optional[str] = None) -> ValidationResult:
        """
        Validate file format using python-magic or file extension fallback.
        
        Args:
            file_path: Path to the file to validate
            original_filename: Original filename for extension-based detection
            
        Returns:
            ValidationResult with validation details
        """
        try:
            if MAGIC_AVAILABLE and self.magic_mime is not None:
                # Use python-magic for accurate detection
                mime_type = self.magic_mime.from_file(file_path)
                file_description = self.magic_type.from_file(file_path)
                
                # Check if MIME type is allowed
                if mime_type not in settings.allowed_file_types:
                    return ValidationResult(
                        is_valid=False,
                        detected_format=mime_type,
                        errors=[f"File type '{mime_type}' is not supported"],
                        warnings=[]
                    )
                
                # Map to internal FileType
                file_type = self.mime_to_filetype.get(mime_type)
                if file_type is None:
                    return ValidationResult(
                        is_valid=False,
                        detected_format=mime_type,
                        errors=[f"File type '{mime_type}' mapping not found"],
                        warnings=[]
                    )
                
                detected_format = mime_type
            else:
                # Fallback to extension-based detection
                # Use original filename if provided, otherwise use file path
                filename_for_extension = original_filename or file_path
                file_extension = Path(filename_for_extension).suffix.lower()
                file_type = self.extension_to_filetype.get(file_extension)
                
                if file_type is None:
                    return ValidationResult(
                        is_valid=False,
                        detected_format=file_extension,
                        errors=[f"File extension '{file_extension}' is not supported"],
                        warnings=["File type detection using extension only (python-magic not available)"]
                    )
                
                detected_format = file_extension
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            warnings = []
            if not MAGIC_AVAILABLE:
                warnings.append("File type detection using extension only (python-magic not available)")
            
            return ValidationResult(
                is_valid=True,
                file_type=file_type,
                detected_format=detected_format,
                size=file_size,
                errors=[],
                warnings=warnings
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"File validation error: {str(e)}"],
                warnings=[]
            )
    
    def validate_file_size(self, file_size: int) -> ValidationResult:
        """
        Validate file size against configured limits.
        
        Args:
            file_size: Size of the file in bytes
            
        Returns:
            ValidationResult with size validation details
        """
        if file_size > settings.max_file_size:
            max_size_mb = settings.max_file_size / (1024 * 1024)
            current_size_mb = file_size / (1024 * 1024)
            return ValidationResult(
                is_valid=False,
                size=file_size,
                errors=[f"File size ({current_size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb:.1f}MB)"],
                warnings=[]
            )
        
        if file_size == 0:
            return ValidationResult(
                is_valid=False,
                size=file_size,
                errors=["File is empty"],
                warnings=[]
            )
        
        warnings = []
        if file_size > settings.max_file_size * 0.8:  # Warn at 80% of limit
            max_size_mb = settings.max_file_size / (1024 * 1024)
            warnings.append(f"File size is approaching the maximum limit ({max_size_mb:.1f}MB)")
        
        return ValidationResult(
            is_valid=True,
            size=file_size,
            errors=[],
            warnings=warnings
        )
    
    def validate_filename(self, filename: str) -> ValidationResult:
        """
        Validate filename for security and format compliance.
        
        Args:
            filename: Name of the file
            
        Returns:
            ValidationResult with filename validation details
        """
        errors = []
        warnings = []
        
        # Check for dangerous characters
        dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*', '\0']
        for char in dangerous_chars:
            if char in filename:
                errors.append(f"Filename contains dangerous character: '{char}'")
        
        # Check filename length
        if len(filename) > 255:
            errors.append("Filename is too long (maximum 255 characters)")
        
        if len(filename) == 0:
            errors.append("Filename cannot be empty")
        
        # Check for reserved names (Windows)
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1, 10)] + [f'LPT{i}' for i in range(1, 10)]
        name_without_ext = filename.split('.')[0].upper()
        if name_without_ext in reserved_names:
            errors.append(f"Filename uses reserved name: '{name_without_ext}'")
        
        # Check for hidden files
        if filename.startswith('.'):
            warnings.append("Filename starts with dot (hidden file)")
        
        # Check for multiple extensions
        if filename.count('.') > 1:
            warnings.append("Filename has multiple extensions")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


class UploadManager:
    """Manages document uploads with validation, progress tracking, and secure storage."""
    
    def __init__(self, storage_directory: Optional[str] = None):
        """
        Initialize upload manager.
        
        Args:
            storage_directory: Directory for storing documents
        """
        self.validator = FileValidator()
        self.storage = SecureStorage(storage_directory)
        self.progress_tracker = ProgressTracker()
        self.batch_tracker = BatchProgressTracker()
        
        # Active uploads tracking
        self._active_uploads: Dict[UUID, Dict[str, Any]] = {}
        self._upload_lock = asyncio.Lock()
    
    async def upload_document(self, file_data: Union[bytes, BinaryIO], 
                            filename: str,
                            upload_metadata: Optional[UploadMetadata] = None,
                            encrypt: bool = True,
                            password: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a document with validation and secure storage.
        
        Args:
            file_data: File content as bytes or file-like object
            filename: Original filename
            upload_metadata: Optional metadata for the upload
            encrypt: Whether to encrypt the stored document
            password: Password for encryption (generated if not provided)
            
        Returns:
            Dictionary containing upload result and document information
        """
        # Generate document ID
        document_id = uuid4()
        
        try:
            # Convert file data to bytes if needed
            if hasattr(file_data, 'read'):
                content = file_data.read()
            else:
                content = file_data
            
            # Validate filename first (before creating temp file)
            filename_validation = self.validator.validate_filename(filename)
            if not filename_validation.is_valid:
                return {
                    "success": False,
                    "document_id": str(document_id),
                    "errors": filename_validation.errors,
                    "warnings": filename_validation.warnings
                }
            
            # Validate file size early (before creating temp file)
            size_validation = self.validator.validate_file_size(len(content))
            if not size_validation.is_valid:
                return {
                    "success": False,
                    "document_id": str(document_id),
                    "errors": size_validation.errors,
                    "warnings": size_validation.warnings
                }
            
            # Create temporary file for format validation (use safe suffix)
            safe_suffix = ".tmp"  # Use safe suffix instead of potentially dangerous filename
            fd, temp_path = self.storage.create_temp_file(suffix=safe_suffix)
            try:
                with os.fdopen(fd, 'wb') as temp_file:
                    temp_file.write(content)
                
                # Validate file format
                format_validation = self.validator.validate_file_format(temp_path, filename)
                if not format_validation.is_valid:
                    return {
                        "success": False,
                        "document_id": str(document_id),
                        "errors": format_validation.errors,
                        "warnings": format_validation.warnings
                    }
                
                # Create progress tracker
                progress_id = await self.progress_tracker.create_progress(
                    filename=filename,
                    total_size=len(content),
                    metadata={"document_id": str(document_id)}
                )
                
                await self.progress_tracker.start_progress(progress_id)
                
                # Store document securely
                storage_info = await self.storage.move_temp_to_storage(
                    temp_path, document_id, encrypt, password
                )
                
                # Create document model
                document = Document(
                    id=None,  # Will be set by database
                    filename=filename,
                    file_type=format_validation.file_type,
                    size=len(content),
                    upload_timestamp=datetime.utcnow(),
                    hash=storage_info["hash"],
                    processing_status=ProcessingStatus.PENDING,
                    upload_metadata=upload_metadata
                )
                
                await self.progress_tracker.complete_progress(progress_id)
                
                # Combine all warnings
                all_warnings = (filename_validation.warnings + 
                              format_validation.warnings + 
                              size_validation.warnings)
                
                return {
                    "success": True,
                    "document_id": str(document_id),
                    "document": document,
                    "storage_info": storage_info,
                    "progress_id": str(progress_id),
                    "warnings": all_warnings
                }
                
            finally:
                # Clean up temp file if it still exists
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            return {
                "success": False,
                "document_id": str(document_id),
                "errors": [f"Upload failed: {str(e)}"],
                "warnings": []
            }
    
    async def upload_batch(self, files: List[Dict[str, Any]], 
                         batch_metadata: Optional[Dict[str, Any]] = None,
                         encrypt: bool = True) -> Dict[str, Any]:
        """
        Upload multiple documents as a batch.
        
        Args:
            files: List of file dictionaries with 'data', 'filename', and optional 'metadata'
            batch_metadata: Optional metadata for the entire batch
            encrypt: Whether to encrypt stored documents
            
        Returns:
            Dictionary containing batch upload results
        """
        batch_id = uuid4()
        
        # Create batch progress tracker
        await self.batch_tracker.create_batch(batch_id, len(files))
        
        # Track individual uploads
        upload_results = []
        successful_uploads = 0
        failed_uploads = 0
        
        # Process files concurrently (with limit)
        semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)
        
        async def upload_single_file(file_info: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                # Create upload metadata with batch ID
                upload_metadata = UploadMetadata(
                    batch_id=batch_id,
                    **(file_info.get('metadata', {}))
                )
                
                result = await self.upload_document(
                    file_data=file_info['data'],
                    filename=file_info['filename'],
                    upload_metadata=upload_metadata,
                    encrypt=encrypt
                )
                
                # Add file progress to batch tracker
                if result.get('progress_id'):
                    progress_info = await self.progress_tracker.get_progress(
                        UUID(result['progress_id'])
                    )
                    if progress_info:
                        await self.batch_tracker.add_file_to_batch(
                            batch_id, UUID(result['progress_id']), progress_info
                        )
                
                return result
        
        # Execute uploads concurrently
        tasks = [upload_single_file(file_info) for file_info in files]
        upload_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(upload_results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "filename": files[i].get('filename', 'unknown'),
                    "errors": [f"Upload exception: {str(result)}"],
                    "warnings": []
                })
                failed_uploads += 1
            else:
                processed_results.append(result)
                if result.get('success', False):
                    successful_uploads += 1
                else:
                    failed_uploads += 1
        
        # Update batch progress
        await self.batch_tracker.update_batch_progress(batch_id)
        
        batch_progress = await self.batch_tracker.get_batch_progress(batch_id)
        
        return {
            "success": True,
            "batch_id": str(batch_id),
            "total_files": len(files),
            "successful_uploads": successful_uploads,
            "failed_uploads": failed_uploads,
            "upload_results": processed_results,
            "batch_progress": batch_progress,
            "batch_metadata": batch_metadata
        }
    
    async def get_upload_progress(self, progress_id: UUID) -> Optional[ProgressInfo]:
        """
        Get progress information for an upload.
        
        Args:
            progress_id: UUID of the progress tracker
            
        Returns:
            ProgressInfo if found, None otherwise
        """
        return await self.progress_tracker.get_progress(progress_id)
    
    async def get_batch_status(self, batch_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get status information for a batch upload.
        
        Args:
            batch_id: UUID of the batch
            
        Returns:
            Batch status information if found, None otherwise
        """
        return await self.batch_tracker.get_batch_progress(batch_id)
    
    async def cancel_upload(self, progress_id: UUID) -> bool:
        """
        Cancel an ongoing upload.
        
        Args:
            progress_id: UUID of the progress tracker
            
        Returns:
            True if upload was cancelled, False if not found or already completed
        """
        progress = await self.progress_tracker.get_progress(progress_id)
        if progress is None:
            return False
        
        if progress.status.value in ["completed", "failed", "cancelled"]:
            return False
        
        await self.progress_tracker.cancel_progress(progress_id)
        return True
    
    def validate_format(self, file_path: str, original_filename: Optional[str] = None) -> ValidationResult:
        """
        Validate file format without uploading.
        
        Args:
            file_path: Path to the file to validate
            original_filename: Original filename for extension-based detection
            
        Returns:
            ValidationResult with validation details
        """
        return self.validator.validate_file_format(file_path, original_filename)
    
    async def cleanup_old_progress(self, max_age_seconds: int = 3600) -> None:
        """
        Clean up old progress entries.
        
        Args:
            max_age_seconds: Maximum age in seconds for completed entries
        """
        await self.progress_tracker.cleanup_completed(max_age_seconds)
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary containing storage statistics
        """
        return await self.storage.get_storage_stats()
    
    async def verify_document_integrity(self, document_id: UUID, 
                                      expected_hash: str,
                                      password: Optional[str] = None,
                                      salt: Optional[str] = None) -> bool:
        """
        Verify document integrity.
        
        Args:
            document_id: UUID of the document
            expected_hash: Expected SHA-256 hash
            password: Password for decryption (if encrypted)
            salt: Salt for key derivation (if encrypted)
            
        Returns:
            True if integrity is verified, False otherwise
        """
        return await self.storage.verify_document_integrity(
            document_id, expected_hash, password, salt
        )
    
    async def delete_document(self, document_id: UUID) -> bool:
        """
        Delete a document from storage.
        
        Args:
            document_id: UUID of the document
            
        Returns:
            True if document was deleted, False if not found
        """
        return await self.storage.delete_document(document_id)
    
    def generate_hash(self, content: Union[bytes, str]) -> str:
        """
        Generate SHA-256 hash for document content.
        
        Args:
            content: Document content
            
        Returns:
            SHA-256 hash as hexadecimal string
        """
        return hash_document(content)