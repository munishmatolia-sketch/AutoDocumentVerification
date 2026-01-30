"""Secure storage for uploaded documents."""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
# UUID removed - using integer IDs and timestamp-based strings

from ..core.config import settings
from ..utils.crypto import (
    DocumentEncryption, 
    DocumentHasher, 
    SecureRandom,
    hash_document
)


class SecureStorage:
    """Handles secure storage of uploaded documents with encryption."""
    
    def __init__(self, storage_directory: Optional[str] = None):
        """
        Initialize secure storage.
        
        Args:
            storage_directory: Directory for storing documents (uses config default if None)
        """
        self.storage_directory = Path(storage_directory or settings.upload_directory)
        self.storage_directory.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        self.documents_dir = self.storage_directory / "documents"
        self.metadata_dir = self.storage_directory / "metadata"
        self.temp_dir = self.storage_directory / "temp"
        
        for directory in [self.documents_dir, self.metadata_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def generate_storage_path(self, document_id: int, encrypted: bool = True) -> Path:
        """
        Generate storage path for a document.
        
        Args:
            document_id: Integer ID of the document
            encrypted: Whether the document will be encrypted
            
        Returns:
            Path where the document should be stored
        """
        # Use document ID for directory structure
        doc_id_str = str(document_id).zfill(8)  # Pad to 8 digits
        subdir = doc_id_str[:2]
        
        storage_subdir = self.documents_dir / subdir
        storage_subdir.mkdir(parents=True, exist_ok=True)
        
        extension = ".enc" if encrypted else ".bin"
        return storage_subdir / f"{document_id}{extension}"
    
    def generate_metadata_path(self, document_id: int) -> Path:
        """
        Generate metadata storage path for a document.
        
        Args:
            document_id: Integer ID of the document
            
        Returns:
            Path where the document metadata should be stored
        """
        doc_id_str = str(document_id).zfill(8)  # Pad to 8 digits
        subdir = doc_id_str[:2]
        
        metadata_subdir = self.metadata_dir / subdir
        metadata_subdir.mkdir(parents=True, exist_ok=True)
        
        return metadata_subdir / f"{document_id}.json"
    
    async def store_document(self, content: bytes, document_id: int, 
                           encrypt: bool = True, 
                           password: Optional[str] = None) -> Dict[str, Any]:
        """
        Store document content securely.
        
        Args:
            content: Document content as bytes
            document_id: Integer ID for the document
            encrypt: Whether to encrypt the content
            password: Password for encryption (generated if not provided)
            
        Returns:
            Dictionary containing storage information
        """
        storage_path = self.generate_storage_path(document_id, encrypt)
        
        # Generate document hash before encryption
        document_hash = hash_document(content)
        
        storage_info = {
            "document_id": str(document_id),
            "storage_path": str(storage_path),
            "encrypted": encrypt,
            "hash": document_hash,
            "size": len(content)
        }
        
        if encrypt:
            if password is None:
                password = SecureRandom.generate_token(32)
            
            # Encrypt content
            key, salt = DocumentEncryption.derive_key_from_password(password)
            encrypted_content = DocumentEncryption.encrypt_content(content, key)
            
            # Store encrypted content
            with open(storage_path, 'wb') as f:
                f.write(encrypted_content)
            
            storage_info.update({
                "encryption_key": password,
                "salt": salt.hex(),
                "encrypted_size": len(encrypted_content)
            })
        else:
            # Store content without encryption
            with open(storage_path, 'wb') as f:
                f.write(content)
        
        # Set restrictive file permissions
        os.chmod(storage_path, 0o600)
        
        return storage_info
    
    async def retrieve_document(self, document_id: int, 
                              password: Optional[str] = None,
                              salt: Optional[str] = None) -> Optional[bytes]:
        """
        Retrieve document content.
        
        Args:
            document_id: Integer ID of the document
            password: Password for decryption (if encrypted)
            salt: Salt for key derivation (if encrypted)
            
        Returns:
            Document content as bytes, or None if not found
        """
        # Try encrypted path first
        encrypted_path = self.generate_storage_path(document_id, encrypted=True)
        unencrypted_path = self.generate_storage_path(document_id, encrypted=False)
        
        storage_path = None
        is_encrypted = False
        
        if encrypted_path.exists():
            storage_path = encrypted_path
            is_encrypted = True
        elif unencrypted_path.exists():
            storage_path = unencrypted_path
            is_encrypted = False
        
        if storage_path is None:
            return None
        
        with open(storage_path, 'rb') as f:
            content = f.read()
        
        if is_encrypted:
            if password is None or salt is None:
                raise ValueError("Password and salt required for encrypted document")
            
            salt_bytes = bytes.fromhex(salt)
            key, _ = DocumentEncryption.derive_key_from_password(password, salt_bytes)
            content = DocumentEncryption.decrypt_content(content, key)
        
        return content
    
    async def delete_document(self, document_id: int) -> bool:
        """
        Delete document and its metadata.
        
        Args:
            document_id: Integer ID of the document
            
        Returns:
            True if document was deleted, False if not found
        """
        deleted = False
        
        # Try to delete both encrypted and unencrypted versions
        for encrypted in [True, False]:
            storage_path = self.generate_storage_path(document_id, encrypted)
            if storage_path.exists():
                # Secure deletion by overwriting with random data
                await self._secure_delete(storage_path)
                deleted = True
        
        # Delete metadata
        metadata_path = self.generate_metadata_path(document_id)
        if metadata_path.exists():
            metadata_path.unlink()
            deleted = True
        
        return deleted
    
    async def _secure_delete(self, file_path: Path) -> None:
        """
        Securely delete a file by overwriting with random data.
        
        Args:
            file_path: Path to the file to delete
        """
        if not file_path.exists():
            return
        
        file_size = file_path.stat().st_size
        
        # Overwrite with random data multiple times
        for _ in range(3):
            with open(file_path, 'r+b') as f:
                f.seek(0)
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())
        
        # Finally delete the file
        file_path.unlink()
    
    async def verify_document_integrity(self, document_id: int, 
                                      expected_hash: str,
                                      password: Optional[str] = None,
                                      salt: Optional[str] = None) -> bool:
        """
        Verify document integrity using hash comparison.
        
        Args:
            document_id: Integer ID of the document
            expected_hash: Expected SHA-256 hash
            password: Password for decryption (if encrypted)
            salt: Salt for key derivation (if encrypted)
            
        Returns:
            True if integrity is verified, False otherwise
        """
        try:
            content = await self.retrieve_document(document_id, password, salt)
            if content is None:
                return False
            
            actual_hash = hash_document(content)
            return actual_hash.lower() == expected_hash.lower()
        except Exception:
            return False
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary containing storage statistics
        """
        total_files = 0
        total_size = 0
        encrypted_files = 0
        
        for root, dirs, files in os.walk(self.documents_dir):
            for file in files:
                file_path = Path(root) / file
                total_files += 1
                total_size += file_path.stat().st_size
                
                if file.endswith('.enc'):
                    encrypted_files += 1
        
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "encrypted_files": encrypted_files,
            "unencrypted_files": total_files - encrypted_files,
            "storage_directory": str(self.storage_directory)
        }
    
    async def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up temporary files older than max_age_hours.
        
        Args:
            max_age_hours: Maximum age in hours for temporary files
            
        Returns:
            Number of files cleaned up
        """
        import time
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_count = 0
        
        for file_path in self.temp_dir.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    await self._secure_delete(file_path)
                    cleaned_count += 1
        
        return cleaned_count
    
    def create_temp_file(self, suffix: str = ".tmp") -> Tuple[int, str]:
        """
        Create a temporary file in the secure temp directory.
        
        Args:
            suffix: File suffix for the temporary file
            
        Returns:
            Tuple of (file_descriptor, file_path)
        """
        fd, temp_path = tempfile.mkstemp(suffix=suffix, dir=self.temp_dir)
        os.chmod(temp_path, 0o600)
        return fd, temp_path
    
    async def move_temp_to_storage(self, temp_path: str, document_id: int,
                                 encrypt: bool = True,
                                 password: Optional[str] = None) -> Dict[str, Any]:
        """
        Move a temporary file to secure storage.
        
        Args:
            temp_path: Path to the temporary file
            document_id: Integer ID for the document
            encrypt: Whether to encrypt the content
            password: Password for encryption
            
        Returns:
            Dictionary containing storage information
        """
        with open(temp_path, 'rb') as f:
            content = f.read()
        
        # Store the content
        storage_info = await self.store_document(content, document_id, encrypt, password)
        
        # Securely delete the temporary file
        await self._secure_delete(Path(temp_path))
        
        return storage_info