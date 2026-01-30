"""Unit tests for Upload Manager edge cases."""

import asyncio
import os
import tempfile
import pytest
from pathlib import Path
from uuid import uuid4, UUID
from unittest.mock import Mock, patch, AsyncMock

from src.document_forensics.upload.manager import UploadManager, FileValidator
from src.document_forensics.core.models import UploadMetadata, FileType
from src.document_forensics.core.config import settings


class TestFileValidator:
    """Test file format validation edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = FileValidator()
    
    def test_validate_empty_file(self, tmp_path):
        """Test validation of empty file."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_bytes(b"")
        
        result = self.validator.validate_file_size(0)
        assert not result.is_valid
        assert "File is empty" in result.errors
    
    def test_validate_oversized_file(self):
        """Test validation of file exceeding size limit."""
        oversized = settings.max_file_size + 1
        
        result = self.validator.validate_file_size(oversized)
        assert not result.is_valid
        assert "exceeds maximum allowed size" in result.errors[0]
    
    def test_validate_file_at_size_limit(self):
        """Test validation of file exactly at size limit."""
        exact_limit = settings.max_file_size
        
        result = self.validator.validate_file_size(exact_limit)
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_file_near_size_limit(self):
        """Test validation of file near size limit (80% threshold)."""
        near_limit = int(settings.max_file_size * 0.85)  # Above 80% threshold
        
        result = self.validator.validate_file_size(near_limit)
        assert result.is_valid
        assert len(result.warnings) > 0
        assert "approaching the maximum limit" in result.warnings[0]
    
    def test_validate_dangerous_filename_characters(self):
        """Test validation of filenames with dangerous characters."""
        dangerous_filenames = [
            "file/../../../etc/passwd",
            "file<script>alert('xss')</script>.txt",
            'file"with"quotes.txt',
            "file|with|pipes.txt",
            "file?with?questions.txt",
            "file*with*wildcards.txt",
            "file\x00with\x00nulls.txt"
        ]
        
        for filename in dangerous_filenames:
            result = self.validator.validate_filename(filename)
            assert not result.is_valid, f"Filename should be invalid: {filename}"
            assert len(result.errors) > 0
    
    def test_validate_reserved_filenames(self):
        """Test validation of Windows reserved filenames."""
        reserved_names = ["CON.txt", "PRN.pdf", "AUX.doc", "NUL.jpg", "COM1.txt", "LPT1.txt"]
        
        for filename in reserved_names:
            result = self.validator.validate_filename(filename)
            assert not result.is_valid, f"Reserved filename should be invalid: {filename}"
            assert "reserved name" in result.errors[0]
    
    def test_validate_long_filename(self):
        """Test validation of extremely long filename."""
        long_filename = "a" * 300 + ".txt"
        
        result = self.validator.validate_filename(long_filename)
        assert not result.is_valid
        assert "too long" in result.errors[0]
    
    def test_validate_empty_filename(self):
        """Test validation of empty filename."""
        result = self.validator.validate_filename("")
        assert not result.is_valid
        assert "cannot be empty" in result.errors[0]
    
    def test_validate_hidden_file_warning(self):
        """Test validation of hidden files (starting with dot)."""
        result = self.validator.validate_filename(".hidden_file.txt")
        assert result.is_valid  # Should be valid but with warning
        assert len(result.warnings) > 0
        assert "hidden file" in result.warnings[0]
    
    def test_validate_multiple_extensions_warning(self):
        """Test validation of files with multiple extensions."""
        result = self.validator.validate_filename("file.tar.gz")
        assert result.is_valid  # Should be valid but with warning
        assert len(result.warnings) > 0
        assert "multiple extensions" in result.warnings[0]
    
    def test_validate_unsupported_file_format(self, tmp_path):
        """Test validation of unsupported file format."""
        # Create a file with unsupported content
        unsupported_file = tmp_path / "test.exe"
        unsupported_file.write_bytes(b"MZ\x90\x00")  # PE executable header
        
        # Import the MAGIC_AVAILABLE flag to check if magic is available
        from src.document_forensics.upload.manager import MAGIC_AVAILABLE
        
        if MAGIC_AVAILABLE:
            with patch.object(self.validator.magic_mime, 'from_file', return_value='application/x-executable'):
                result = self.validator.validate_file_format(str(unsupported_file))
                assert not result.is_valid
                assert "not supported" in result.errors[0]
        else:
            # When magic is not available, it uses extension-based detection
            result = self.validator.validate_file_format(str(unsupported_file))
            assert not result.is_valid
            assert "not supported" in result.errors[0]
    
    def test_validate_corrupted_file(self, tmp_path):
        """Test validation of corrupted file that causes magic to fail."""
        corrupted_file = tmp_path / "corrupted.pdf"
        corrupted_file.write_bytes(b"corrupted content")
        
        # Import the MAGIC_AVAILABLE flag to check if magic is available
        from src.document_forensics.upload.manager import MAGIC_AVAILABLE
        
        if MAGIC_AVAILABLE:
            with patch.object(self.validator.magic_mime, 'from_file', side_effect=Exception("Magic failed")):
                result = self.validator.validate_file_format(str(corrupted_file))
                assert not result.is_valid
                assert "File validation error" in result.errors[0]
        else:
            # When magic is not available, extension-based detection should work
            result = self.validator.validate_file_format(str(corrupted_file))
            # Should be valid based on .pdf extension
            assert result.is_valid or "not supported" in str(result.errors)


class TestUploadManager:
    """Test Upload Manager edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.upload_manager = UploadManager(storage_directory=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_upload_empty_file(self):
        """Test uploading an empty file."""
        result = await self.upload_manager.upload_document(
            file_data=b"",
            filename="empty.txt"
        )
        
        assert not result["success"]
        assert "File is empty" in str(result["errors"])
    
    @pytest.mark.asyncio
    async def test_upload_oversized_file(self):
        """Test uploading a file that exceeds size limit."""
        # Create content larger than max size
        large_content = b"x" * (settings.max_file_size + 1)
        
        result = await self.upload_manager.upload_document(
            file_data=large_content,
            filename="large.txt"
        )
        
        assert not result["success"]
        assert "exceeds maximum allowed size" in str(result["errors"])
    
    @pytest.mark.asyncio
    async def test_upload_invalid_filename(self):
        """Test uploading with invalid filename."""
        result = await self.upload_manager.upload_document(
            file_data=b"valid content",
            filename="invalid/../../../etc/passwd"
        )
        
        assert not result["success"]
        # Should fail at filename validation stage
        errors = result.get("errors", [])
        assert len(errors) > 0
        assert any("dangerous character" in str(error) or "invalid characters" in str(error) for error in errors)
    
    @pytest.mark.asyncio
    async def test_upload_with_file_like_object(self, sample_text_content):
        """Test uploading with file-like object."""
        from io import BytesIO
        
        file_obj = BytesIO(sample_text_content.encode())
        
        result = await self.upload_manager.upload_document(
            file_data=file_obj,
            filename="test.txt"
        )
        
        # Debug: print result if test fails
        if not result.get("success"):
            print(f"Upload failed: {result}")
        
        assert result["success"], f"Upload failed with errors: {result.get('errors', 'Unknown error')}"
        assert result["document"].filename == "test.txt"
        assert result["document"].file_type == FileType.TXT
    
    @pytest.mark.asyncio
    async def test_upload_with_metadata(self, sample_text_content):
        """Test uploading with upload metadata."""
        metadata = UploadMetadata(
            description="Test upload",
            tags=["test", "sample"],
            priority=8,
            user_id="test_user"
        )
        
        result = await self.upload_manager.upload_document(
            file_data=sample_text_content.encode(),
            filename="test.txt",
            upload_metadata=metadata
        )
        
        assert result["success"]
        assert result["document"].upload_metadata.description == "Test upload"
        assert result["document"].upload_metadata.priority == 8
    
    @pytest.mark.asyncio
    async def test_upload_with_encryption_disabled(self, sample_text_content):
        """Test uploading without encryption."""
        result = await self.upload_manager.upload_document(
            file_data=sample_text_content.encode(),
            filename="test.txt",
            encrypt=False
        )
        
        assert result["success"]
        assert not result["storage_info"]["encrypted"]
    
    @pytest.mark.asyncio
    async def test_upload_with_custom_password(self, sample_text_content):
        """Test uploading with custom encryption password."""
        custom_password = "my_secure_password_123"
        
        result = await self.upload_manager.upload_document(
            file_data=sample_text_content.encode(),
            filename="test.txt",
            encrypt=True,
            password=custom_password
        )
        
        assert result["success"]
        assert result["storage_info"]["encrypted"]
        assert result["storage_info"]["encryption_key"] == custom_password
    
    @pytest.mark.asyncio
    async def test_batch_upload_empty_list(self):
        """Test batch upload with empty file list."""
        result = await self.upload_manager.upload_batch([])
        
        assert result["success"]
        assert result["total_files"] == 0
        assert result["successful_uploads"] == 0
        assert result["failed_uploads"] == 0
    
    @pytest.mark.asyncio
    async def test_batch_upload_mixed_results(self, sample_text_content):
        """Test batch upload with mix of valid and invalid files."""
        files = [
            {
                "data": sample_text_content.encode(),
                "filename": "valid.txt"
            },
            {
                "data": b"",  # Empty file - should fail
                "filename": "empty.txt"
            },
            {
                "data": sample_text_content.encode(),
                "filename": "invalid/../path.txt"  # Invalid filename - should fail
            }
        ]
        
        result = await self.upload_manager.upload_batch(files)
        
        assert result["success"]
        assert result["total_files"] == 3
        assert result["successful_uploads"] == 1
        assert result["failed_uploads"] == 2
    
    @pytest.mark.asyncio
    async def test_batch_upload_with_exception(self, sample_text_content):
        """Test batch upload when one file causes an exception."""
        files = [
            {
                "data": sample_text_content.encode(),
                "filename": "valid.txt"
            }
        ]
        
        # Mock storage to raise exception
        with patch.object(self.upload_manager.storage, 'move_temp_to_storage', 
                         side_effect=Exception("Storage error")):
            result = await self.upload_manager.upload_batch(files)
            
            assert result["success"]
            assert result["failed_uploads"] == 1
            assert "Storage error" in str(result["upload_results"][0]["errors"])
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_progress(self):
        """Test getting progress for non-existent upload."""
        fake_id = uuid4()
        progress = await self.upload_manager.get_upload_progress(fake_id)
        assert progress is None
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_batch_status(self):
        """Test getting status for non-existent batch."""
        fake_id = uuid4()
        status = await self.upload_manager.get_batch_status(fake_id)
        assert status is None
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_upload(self):
        """Test cancelling non-existent upload."""
        fake_id = uuid4()
        result = await self.upload_manager.cancel_upload(fake_id)
        assert not result
    
    @pytest.mark.asyncio
    async def test_cancel_completed_upload(self, sample_text_content):
        """Test cancelling already completed upload."""
        # First upload a file
        result = await self.upload_manager.upload_document(
            file_data=sample_text_content.encode(),
            filename="test.txt"
        )
        
        assert result["success"]
        progress_id = UUID(result["progress_id"])
        
        # Try to cancel completed upload
        cancel_result = await self.upload_manager.cancel_upload(progress_id)
        assert not cancel_result
    
    @pytest.mark.asyncio
    async def test_verify_nonexistent_document(self):
        """Test verifying integrity of non-existent document."""
        fake_id = uuid4()
        result = await self.upload_manager.verify_document_integrity(
            fake_id, "fake_hash"
        )
        assert not result
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self):
        """Test deleting non-existent document."""
        fake_id = uuid4()
        result = await self.upload_manager.delete_document(fake_id)
        assert not result
    
    def test_generate_hash_string_input(self):
        """Test hash generation with string input."""
        test_string = "Hello, World!"
        hash_result = self.upload_manager.generate_hash(test_string)
        
        assert isinstance(hash_result, str)
        assert len(hash_result) == 64  # SHA-256 hex length
        
        # Verify consistency
        hash_result2 = self.upload_manager.generate_hash(test_string)
        assert hash_result == hash_result2
    
    def test_generate_hash_bytes_input(self):
        """Test hash generation with bytes input."""
        test_bytes = b"Hello, World!"
        hash_result = self.upload_manager.generate_hash(test_bytes)
        
        assert isinstance(hash_result, str)
        assert len(hash_result) == 64  # SHA-256 hex length
    
    @pytest.mark.asyncio
    async def test_storage_stats(self, sample_text_content):
        """Test getting storage statistics."""
        # Upload a file first
        await self.upload_manager.upload_document(
            file_data=sample_text_content.encode(),
            filename="test.txt"
        )
        
        stats = await self.upload_manager.get_storage_stats()
        
        assert "total_files" in stats
        assert "total_size_bytes" in stats
        assert "encrypted_files" in stats
        assert "storage_directory" in stats
        assert stats["total_files"] >= 1


class TestProgressTracking:
    """Test progress tracking accuracy and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.upload_manager = UploadManager(storage_directory=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_progress_tracking_accuracy(self, sample_text_content):
        """Test that progress tracking accurately reflects upload progress."""
        content = sample_text_content.encode() * 1000  # Make it larger for better tracking
        
        result = await self.upload_manager.upload_document(
            file_data=content,
            filename="large_test.txt"
        )
        
        assert result["success"]
        progress_id = UUID(result["progress_id"])
        
        # Get final progress
        progress = await self.upload_manager.get_upload_progress(progress_id)
        assert progress is not None
        assert progress.progress_percentage == 100.0
        assert progress.processed_size == len(content)
        assert progress.total_size == len(content)
    
    @pytest.mark.asyncio
    async def test_progress_cleanup(self, sample_text_content):
        """Test cleanup of old progress entries."""
        # Upload a file
        result = await self.upload_manager.upload_document(
            file_data=sample_text_content.encode(),
            filename="test.txt"
        )
        
        assert result["success"]
        progress_id = UUID(result["progress_id"])
        
        # Verify progress exists
        progress = await self.upload_manager.get_upload_progress(progress_id)
        assert progress is not None
        
        # Add a small delay to ensure the progress is old enough
        import time
        time.sleep(0.1)
        
        # Clean up with very short max age (should remove the entry)
        await self.upload_manager.cleanup_old_progress(max_age_seconds=0)
        
        # Progress should be cleaned up
        progress = await self.upload_manager.get_upload_progress(progress_id)
        assert progress is None
    
    @pytest.mark.asyncio
    async def test_batch_progress_tracking(self, sample_text_content):
        """Test batch progress tracking accuracy."""
        files = [
            {"data": sample_text_content.encode(), "filename": f"test_{i}.txt"}
            for i in range(3)
        ]
        
        result = await self.upload_manager.upload_batch(files)
        
        assert result["success"]
        batch_id = UUID(result["batch_id"])
        
        # Get batch status
        status = await self.upload_manager.get_batch_status(batch_id)
        assert status is not None
        assert status["progress_percentage"] == 100.0
        assert status["completed_files"] == 3
        assert status["failed_files"] == 0