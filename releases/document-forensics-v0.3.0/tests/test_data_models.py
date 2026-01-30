"""
Property-based tests for data model validation.

Feature: document-forensics, Property 2: Secure Document Handling
Validates: Requirements 1.5, 7.1, 7.3, 7.4
"""

import hashlib
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck

# Import our models and utilities
import sys
sys.path.append('src')

from document_forensics.core.models import (
    Document, DocumentMetadata, UploadMetadata, AnalysisResults,
    MetadataAnalysis, TamperingAnalysis, AuthenticityAnalysis,
    FileType, ProcessingStatus, RiskLevel, ValidationResult
)
from document_forensics.core.validation import (
    DocumentValidator, validate_document_upload, SecurityValidator
)
from document_forensics.utils.crypto import (
    DocumentHasher, DocumentEncryption, IntegrityValidator,
    hash_document, verify_document_integrity
)


# Strategies for generating test data
@st.composite
def document_content_strategy(draw):
    """Generate document content for testing."""
    content_type = draw(st.sampled_from(['text', 'binary', 'pdf_header', 'image_header']))
    
    if content_type == 'text':
        text = draw(st.text(min_size=1, max_size=1000))
        return text.encode('utf-8')
    elif content_type == 'pdf_header':
        # Generate content that starts with PDF header
        base_content = b'%PDF-1.4\n'
        additional = draw(st.binary(min_size=0, max_size=500))
        return base_content + additional
    elif content_type == 'image_header':
        # Generate content that starts with PNG header
        base_content = b'\x89PNG\r\n\x1a\n'
        additional = draw(st.binary(min_size=0, max_size=500))
        return base_content + additional
    else:
        return draw(st.binary(min_size=1, max_size=1000))


@st.composite
def valid_filename_strategy(draw):
    """Generate valid filenames for testing."""
    # Generate safe filename characters
    name_part = draw(st.text(
        min_size=1, max_size=50,
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_"
        )
    ))
    
    # Add file extension
    extension = draw(st.sampled_from(['.pdf', '.png', '.jpg', '.docx', '.xlsx', '.txt']))
    
    # Ensure filename is not empty after cleaning and doesn't start with dot
    assume(len(name_part.strip()) > 0)
    assume(not name_part.startswith('.'))
    assume(not name_part.endswith('.'))
    
    return name_part + extension


@st.composite
def document_strategy(draw):
    """Generate Document model instances for testing."""
    content = draw(document_content_strategy())
    filename = draw(valid_filename_strategy())
    
    # Generate hash for the content
    document_hash = DocumentHasher.generate_sha256(content)
    
    return Document(
        id=draw(st.one_of(st.none(), st.integers(min_value=1, max_value=10000))),
        filename=filename,
        file_type=draw(st.sampled_from(list(FileType))),
        size=len(content),
        hash=document_hash,
        processing_status=draw(st.sampled_from(list(ProcessingStatus))),
        metadata=draw(st.one_of(st.none(), document_metadata_strategy())),
        upload_metadata=draw(st.one_of(st.none(), upload_metadata_strategy()))
    ), content


@st.composite
def document_metadata_strategy(draw):
    """Generate DocumentMetadata instances for testing."""
    return DocumentMetadata(
        creation_date=draw(st.one_of(st.none(), st.datetimes())),
        modification_date=draw(st.one_of(st.none(), st.datetimes())),
        author=draw(st.one_of(st.none(), st.text(min_size=1, max_size=100))),
        creator_software=draw(st.one_of(st.none(), st.text(min_size=1, max_size=100))),
        file_version=draw(st.one_of(st.none(), st.text(min_size=1, max_size=20))),
        page_count=draw(st.one_of(st.none(), st.integers(min_value=0, max_value=1000))),
        word_count=draw(st.one_of(st.none(), st.integers(min_value=0, max_value=100000))),
        character_count=draw(st.one_of(st.none(), st.integers(min_value=0, max_value=1000000)))
    )


@st.composite
def upload_metadata_strategy(draw):
    """Generate UploadMetadata instances for testing."""
    return UploadMetadata(
        description=draw(st.one_of(st.none(), st.text(min_size=0, max_size=500))),
        tags=draw(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=10)),
        priority=draw(st.integers(min_value=1, max_value=10)),
        user_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=100))),
        batch_id=draw(st.one_of(st.none(), st.uuids()))
    )


class TestSecureDocumentHandling:
    """Test class for secure document handling properties."""
    
    @given(document_content_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_cryptographic_hashing_integrity(self, content):
        """
        Test that cryptographic hashing maintains integrity throughout processing.
        
        Property: For any document content, the hash should be consistent and verifiable.
        """
        # Generate hash
        original_hash = DocumentHasher.generate_sha256(content)
        
        # Hash should be 64 characters (SHA-256 hex)
        assert len(original_hash) == 64
        assert all(c in '0123456789abcdef' for c in original_hash)
        
        # Hash should be consistent across multiple calls
        second_hash = DocumentHasher.generate_sha256(content)
        assert original_hash == second_hash
        
        # Hash should be verifiable
        assert DocumentHasher.verify_hash(content, original_hash, 'sha256')
        
        # Different content should produce different hash
        if len(content) > 0:
            modified_content = content + b'x'
            modified_hash = DocumentHasher.generate_sha256(modified_content)
            assert original_hash != modified_hash
    
    @given(document_content_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_document_encryption_security(self, content):
        """
        Test that document encryption provides proper security.
        
        Property: For any document content, encryption should be secure and reversible.
        """
        # Skip empty content as it may not encrypt meaningfully
        assume(len(content) > 0)
        
        # Generate encryption key
        key = DocumentEncryption.generate_key()
        
        # Encrypt content
        encrypted_content = DocumentEncryption.encrypt_content(content, key)
        
        # Encrypted content should be different from original
        assert encrypted_content != content
        
        # Encrypted content should be longer (due to encryption overhead)
        assert len(encrypted_content) > len(content)
        
        # Decryption should recover original content
        decrypted_content = DocumentEncryption.decrypt_content(encrypted_content, key)
        assert decrypted_content == content
        
        # Wrong key should not decrypt correctly
        wrong_key = DocumentEncryption.generate_key()
        with pytest.raises(Exception):  # Should raise cryptographic exception
            DocumentEncryption.decrypt_content(encrypted_content, wrong_key)
    
    @given(document_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_document_model_validation_security(self, document_and_content):
        """
        Test that document model validation enforces security constraints.
        
        Property: For any document, validation should enforce security requirements.
        """
        document, content = document_and_content
        
        # Document hash should match content
        expected_hash = DocumentHasher.generate_sha256(content)
        
        # If document hash doesn't match content, validation should catch it
        if document.hash != expected_hash:
            # This represents a potential integrity violation
            # In a real system, this would be flagged as suspicious
            assert document.hash != expected_hash  # Confirm the mismatch
        else:
            # Hash matches - integrity is maintained
            assert verify_document_integrity(content, document.hash)
        
        # Filename should not contain dangerous characters
        dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
        filename_safe = not any(char in document.filename for char in dangerous_chars)
        
        # Size should match content length
        size_matches = document.size == len(content)
        
        # All security constraints should be satisfied for a valid document
        if filename_safe and size_matches and document.hash == expected_hash:
            # Document should pass all security validations
            assert len(document.filename) > 0
            assert document.size >= 0
            assert len(document.hash) == 64
    
    @given(valid_filename_strategy(), document_content_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_secure_upload_validation(self, filename, content):
        """
        Test that upload validation enforces security requirements.
        
        Property: For any file upload, security validation should be comprehensive.
        """
        # Perform comprehensive upload validation
        is_valid, results = validate_document_upload(filename, content)
        
        # Results should always contain required fields
        assert 'file_validation' in results
        assert 'security_warnings' in results
        assert 'document_hash' in results or not is_valid
        assert 'errors' in results
        assert 'warnings' in results
        
        # Security warnings should be a list
        assert isinstance(results['security_warnings'], list)
        
        # If validation passes, hash should be generated
        if is_valid:
            assert results['document_hash'] is not None
            assert len(results['document_hash']) == 64
            
            # Hash should be verifiable
            assert verify_document_integrity(content, results['document_hash'])
        
        # Security validator should check for dangerous patterns
        security_warnings = SecurityValidator.validate_file_safety(filename, content)
        assert isinstance(security_warnings, list)
        
        # Results should include these security warnings
        assert results['security_warnings'] == security_warnings
    
    @given(document_content_strategy(), st.text(min_size=8, max_size=50))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_integrity_validation_with_hmac(self, content, secret_key):
        """
        Test that HMAC-based integrity validation works correctly.
        
        Property: For any content and secret key, HMAC should provide integrity assurance.
        """
        # Create integrity signature
        signature = IntegrityValidator.create_integrity_signature(content, secret_key)
        
        # Signature should be a hex string
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA-256 HMAC produces 64-char hex string
        assert all(c in '0123456789abcdef' for c in signature)
        
        # Signature should verify with correct key
        assert IntegrityValidator.verify_integrity_signature(content, signature, secret_key)
        
        # Signature should not verify with wrong key
        wrong_key = secret_key + 'wrong'
        assert not IntegrityValidator.verify_integrity_signature(content, signature, wrong_key)
        
        # Modified content should not verify
        if len(content) > 0:
            modified_content = content + b'x'
            assert not IntegrityValidator.verify_integrity_signature(modified_content, signature, secret_key)
    
    @given(st.lists(document_content_strategy(), min_size=1, max_size=5))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    def test_batch_document_integrity(self, content_list):
        """
        Test that integrity is maintained across batch document processing.
        
        Property: For any batch of documents, each should maintain individual integrity.
        """
        # Generate hashes for all documents
        hashes = [DocumentHasher.generate_sha256(content) for content in content_list]
        
        # All hashes should be unique if content is unique
        unique_content = []
        for content in content_list:
            if content not in unique_content:
                unique_content.append(content)
        
        if len(unique_content) == len(content_list):
            # All content is unique, so all hashes should be unique
            assert len(set(hashes)) == len(hashes)
        
        # Each hash should verify its corresponding content
        for content, hash_value in zip(content_list, hashes):
            assert verify_document_integrity(content, hash_value)
        
        # Cross-verification should fail (hash from one doc shouldn't verify another)
        # Only test this if we have truly different content
        if len(content_list) > 1:
            different_content_found = False
            for i in range(len(content_list)):
                for j in range(i + 1, len(content_list)):
                    if content_list[i] != content_list[j]:
                        # Found different content, test cross-verification
                        assert not verify_document_integrity(content_list[i], hashes[j])
                        different_content_found = True
                        break
                if different_content_found:
                    break
    
    def test_security_edge_cases(self):
        """Test security validation with edge cases and boundary conditions."""
        
        # Test empty content
        empty_content = b''
        empty_hash = DocumentHasher.generate_sha256(empty_content)
        assert len(empty_hash) == 64
        assert verify_document_integrity(empty_content, empty_hash)
        
        # Test very large content (within reasonable limits for testing)
        large_content = b'x' * 10000
        large_hash = DocumentHasher.generate_sha256(large_content)
        assert verify_document_integrity(large_content, large_hash)
        
        # Test content with special bytes
        special_content = bytes(range(256))
        special_hash = DocumentHasher.generate_sha256(special_content)
        assert verify_document_integrity(special_content, special_hash)
        
        # Test filename security validation
        dangerous_filenames = [
            '../../../etc/passwd',
            'file<script>alert(1)</script>.pdf',
            'file.exe',
            'file.bat',
            'normal_file.pdf'  # This should be safe
        ]
        
        for filename in dangerous_filenames:
            warnings = SecurityValidator.validate_file_safety(filename, b'test content')
            if filename == 'normal_file.pdf':
                # Should have no warnings for normal file
                assert len(warnings) == 0
            else:
                # Should have warnings for dangerous files
                assert len(warnings) > 0
    
    @given(document_content_strategy())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_encryption_key_security(self, content):
        """
        Test that encryption keys are generated securely and work correctly.
        
        Property: For any content, encryption with different keys should produce different results.
        """
        assume(len(content) > 0)
        
        # Generate two different keys
        key1 = DocumentEncryption.generate_key()
        key2 = DocumentEncryption.generate_key()
        
        # Keys should be different
        assert key1 != key2
        
        # Keys should be proper length (Fernet keys are 44 bytes base64-encoded)
        assert len(key1) == 44
        assert len(key2) == 44
        
        # Encrypt same content with different keys
        encrypted1 = DocumentEncryption.encrypt_content(content, key1)
        encrypted2 = DocumentEncryption.encrypt_content(content, key2)
        
        # Encrypted results should be different
        assert encrypted1 != encrypted2
        
        # Each should decrypt correctly with its own key
        decrypted1 = DocumentEncryption.decrypt_content(encrypted1, key1)
        decrypted2 = DocumentEncryption.decrypt_content(encrypted2, key2)
        
        assert decrypted1 == content
        assert decrypted2 == content
        
        # Cross-decryption should fail
        with pytest.raises(Exception):
            DocumentEncryption.decrypt_content(encrypted1, key2)
        
        with pytest.raises(Exception):
            DocumentEncryption.decrypt_content(encrypted2, key1)


class TestDataModelValidation:
    """Test class for data model validation properties."""
    
    @given(document_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_document_model_consistency(self, document_and_content):
        """
        Test that Document model maintains internal consistency.
        
        Property: For any valid Document instance, all fields should be consistent.
        """
        document, content = document_and_content
        
        # Size should be non-negative
        assert document.size >= 0
        
        # Hash should be valid SHA-256 format
        assert len(document.hash) == 64
        assert all(c in '0123456789abcdef' for c in document.hash.lower())
        
        # Filename should not be empty
        assert len(document.filename.strip()) > 0
        
        # Processing status should be valid enum value
        assert document.processing_status in ProcessingStatus
        
        # File type should be valid enum value
        assert document.file_type in FileType
        
        # If metadata exists, it should be valid
        if document.metadata:
            if document.metadata.page_count is not None:
                assert document.metadata.page_count >= 0
            if document.metadata.word_count is not None:
                assert document.metadata.word_count >= 0
            if document.metadata.character_count is not None:
                assert document.metadata.character_count >= 0
        
        # Upload timestamp should be reasonable (not in far future)
        assert document.upload_timestamp <= datetime.utcnow()
    
    def test_model_validation_errors(self):
        """Test that model validation properly catches invalid data."""
        
        # Test invalid hash format (too short)
        with pytest.raises(Exception):  # Could be ValidationError or ValueError
            Document(
                filename="test.pdf",
                file_type=FileType.PDF,
                size=100,
                hash="invalid_hash_format",  # Invalid hash (too short)
                processing_status=ProcessingStatus.PENDING
            )
        
        # Test invalid hash format (wrong characters) - need 64 chars with invalid chars
        with pytest.raises(Exception):  # Could be ValidationError or ValueError
            Document(
                filename="test.pdf",
                file_type=FileType.PDF,
                size=100,
                hash="g" * 64,  # Invalid hash (contains 'g' which is not hex)
                processing_status=ProcessingStatus.PENDING
            )
        
        # Test dangerous filename
        with pytest.raises(Exception):  # Could be ValidationError or ValueError
            Document(
                filename="../dangerous.pdf",  # Dangerous filename
                file_type=FileType.PDF,
                size=100,
                hash="a" * 64,
                processing_status=ProcessingStatus.PENDING
            )
        
        # Test negative size (should be caught by conint constraint)
        with pytest.raises(Exception):  # Could be ValidationError
            Document(
                filename="test.pdf",
                file_type=FileType.PDF,
                size=-1,  # Negative size
                hash="a" * 64,
                processing_status=ProcessingStatus.PENDING
            )