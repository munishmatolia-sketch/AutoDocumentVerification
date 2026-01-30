"""Cryptographic utilities for document integrity and security."""

import hashlib
import hmac
import secrets
from typing import Union, Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import os


class DocumentHasher:
    """Utility class for generating cryptographic hashes of documents."""
    
    @staticmethod
    def generate_sha256(content: Union[bytes, str]) -> str:
        """
        Generate SHA-256 hash of document content.
        
        Args:
            content: Document content as bytes or string
            
        Returns:
            Hexadecimal string representation of SHA-256 hash
        """
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        hasher = hashlib.sha256()
        hasher.update(content)
        return hasher.hexdigest()
    
    @staticmethod
    def generate_sha512(content: Union[bytes, str]) -> str:
        """
        Generate SHA-512 hash of document content.
        
        Args:
            content: Document content as bytes or string
            
        Returns:
            Hexadecimal string representation of SHA-512 hash
        """
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        hasher = hashlib.sha512()
        hasher.update(content)
        return hasher.hexdigest()
    
    @staticmethod
    def generate_md5(content: Union[bytes, str]) -> str:
        """
        Generate MD5 hash of document content.
        Note: MD5 is cryptographically broken but may be needed for compatibility.
        
        Args:
            content: Document content as bytes or string
            
        Returns:
            Hexadecimal string representation of MD5 hash
        """
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        hasher = hashlib.md5()
        hasher.update(content)
        return hasher.hexdigest()
    
    @staticmethod
    def verify_hash(content: Union[bytes, str], expected_hash: str, 
                   algorithm: str = 'sha256') -> bool:
        """
        Verify that content matches the expected hash.
        
        Args:
            content: Document content to verify
            expected_hash: Expected hash value
            algorithm: Hash algorithm to use ('sha256', 'sha512', 'md5')
            
        Returns:
            True if hash matches, False otherwise
        """
        hash_functions = {
            'sha256': DocumentHasher.generate_sha256,
            'sha512': DocumentHasher.generate_sha512,
            'md5': DocumentHasher.generate_md5
        }
        
        if algorithm not in hash_functions:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
        
        actual_hash = hash_functions[algorithm](content)
        return hmac.compare_digest(actual_hash.lower(), expected_hash.lower())
    
    @staticmethod
    def generate_file_hash(file_path: str, algorithm: str = 'sha256', 
                          chunk_size: int = 8192) -> str:
        """
        Generate hash of a file by reading it in chunks.
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use
            chunk_size: Size of chunks to read at a time
            
        Returns:
            Hexadecimal string representation of file hash
        """
        hash_functions = {
            'sha256': hashlib.sha256,
            'sha512': hashlib.sha512,
            'md5': hashlib.md5
        }
        
        if algorithm not in hash_functions:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
        
        hasher = hash_functions[algorithm]()
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        
        return hasher.hexdigest()


class DocumentEncryption:
    """Utility class for encrypting and decrypting document content."""
    
    @staticmethod
    def generate_key() -> bytes:
        """
        Generate a new encryption key.
        
        Returns:
            32-byte encryption key
        """
        return Fernet.generate_key()
    
    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: Password to derive key from
            salt: Salt for key derivation (generated if not provided)
            
        Returns:
            Tuple of (derived_key, salt)
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    @staticmethod
    def encrypt_content(content: Union[bytes, str], key: bytes) -> bytes:
        """
        Encrypt document content using Fernet symmetric encryption.
        
        Args:
            content: Content to encrypt
            key: Encryption key
            
        Returns:
            Encrypted content as bytes
        """
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        fernet = Fernet(key)
        return fernet.encrypt(content)
    
    @staticmethod
    def decrypt_content(encrypted_content: bytes, key: bytes) -> bytes:
        """
        Decrypt document content using Fernet symmetric encryption.
        
        Args:
            encrypted_content: Encrypted content
            key: Decryption key
            
        Returns:
            Decrypted content as bytes
        """
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_content)
    
    @staticmethod
    def encrypt_with_aes(content: Union[bytes, str], key: bytes, 
                        iv: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Encrypt content using AES-256-CBC.
        
        Args:
            content: Content to encrypt
            key: 32-byte encryption key
            iv: Initialization vector (generated if not provided)
            
        Returns:
            Tuple of (encrypted_content, iv)
        """
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        if iv is None:
            iv = os.urandom(16)
        
        # Pad content to multiple of 16 bytes
        padding_length = 16 - (len(content) % 16)
        padded_content = content + bytes([padding_length] * padding_length)
        
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        encrypted_content = encryptor.update(padded_content) + encryptor.finalize()
        
        return encrypted_content, iv
    
    @staticmethod
    def decrypt_with_aes(encrypted_content: bytes, key: bytes, iv: bytes) -> bytes:
        """
        Decrypt content using AES-256-CBC.
        
        Args:
            encrypted_content: Encrypted content
            key: 32-byte decryption key
            iv: Initialization vector
            
        Returns:
            Decrypted content as bytes
        """
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        padded_content = decryptor.update(encrypted_content) + decryptor.finalize()
        
        # Remove padding
        padding_length = padded_content[-1]
        return padded_content[:-padding_length]


class IntegrityValidator:
    """Utility class for validating document integrity."""
    
    @staticmethod
    def create_integrity_signature(content: Union[bytes, str], secret_key: str) -> str:
        """
        Create HMAC signature for content integrity validation.
        
        Args:
            content: Content to sign
            secret_key: Secret key for HMAC
            
        Returns:
            HMAC signature as hexadecimal string
        """
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        signature = hmac.new(
            secret_key.encode('utf-8'),
            content,
            hashlib.sha256
        )
        return signature.hexdigest()
    
    @staticmethod
    def verify_integrity_signature(content: Union[bytes, str], signature: str, 
                                 secret_key: str) -> bool:
        """
        Verify HMAC signature for content integrity.
        
        Args:
            content: Content to verify
            signature: Expected HMAC signature
            secret_key: Secret key for HMAC
            
        Returns:
            True if signature is valid, False otherwise
        """
        expected_signature = IntegrityValidator.create_integrity_signature(
            content, secret_key
        )
        return hmac.compare_digest(signature.lower(), expected_signature.lower())
    
    @staticmethod
    def generate_checksum(content: Union[bytes, str], algorithm: str = 'sha256') -> str:
        """
        Generate checksum for content integrity verification.
        
        Args:
            content: Content to checksum
            algorithm: Hash algorithm to use
            
        Returns:
            Checksum as hexadecimal string
        """
        return DocumentHasher.generate_sha256(content) if algorithm == 'sha256' else \
               DocumentHasher.generate_sha512(content) if algorithm == 'sha512' else \
               DocumentHasher.generate_md5(content)
    
    @staticmethod
    def verify_checksum(content: Union[bytes, str], expected_checksum: str, 
                       algorithm: str = 'sha256') -> bool:
        """
        Verify content against expected checksum.
        
        Args:
            content: Content to verify
            expected_checksum: Expected checksum value
            algorithm: Hash algorithm used
            
        Returns:
            True if checksum matches, False otherwise
        """
        return DocumentHasher.verify_hash(content, expected_checksum, algorithm)


class SecureRandom:
    """Utility class for generating cryptographically secure random values."""
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """
        Generate cryptographically secure random token.
        
        Args:
            length: Length of token in bytes
            
        Returns:
            URL-safe base64 encoded token
        """
        return base64.urlsafe_b64encode(secrets.token_bytes(length)).decode('ascii')
    
    @staticmethod
    def generate_salt(length: int = 16) -> bytes:
        """
        Generate cryptographically secure random salt.
        
        Args:
            length: Length of salt in bytes
            
        Returns:
            Random salt bytes
        """
        return secrets.token_bytes(length)
    
    @staticmethod
    def generate_iv(length: int = 16) -> bytes:
        """
        Generate cryptographically secure initialization vector.
        
        Args:
            length: Length of IV in bytes
            
        Returns:
            Random IV bytes
        """
        return secrets.token_bytes(length)


# Convenience functions for common operations
def hash_document(content: Union[bytes, str]) -> str:
    """
    Generate SHA-256 hash of document content.
    
    Args:
        content: Document content
        
    Returns:
        SHA-256 hash as hexadecimal string
    """
    return DocumentHasher.generate_sha256(content)


def verify_document_integrity(content: Union[bytes, str], expected_hash: str) -> bool:
    """
    Verify document integrity using SHA-256 hash.
    
    Args:
        content: Document content
        expected_hash: Expected SHA-256 hash
        
    Returns:
        True if integrity is verified, False otherwise
    """
    return DocumentHasher.verify_hash(content, expected_hash, 'sha256')


def encrypt_document(content: Union[bytes, str], password: str) -> Tuple[bytes, bytes]:
    """
    Encrypt document content with password-derived key.
    
    Args:
        content: Document content to encrypt
        password: Password for encryption
        
    Returns:
        Tuple of (encrypted_content, salt)
    """
    key, salt = DocumentEncryption.derive_key_from_password(password)
    encrypted_content = DocumentEncryption.encrypt_content(content, key)
    return encrypted_content, salt


def decrypt_document(encrypted_content: bytes, password: str, salt: bytes) -> bytes:
    """
    Decrypt document content with password-derived key.
    
    Args:
        encrypted_content: Encrypted document content
        password: Password for decryption
        salt: Salt used for key derivation
        
    Returns:
        Decrypted content as bytes
    """
    key, _ = DocumentEncryption.derive_key_from_password(password, salt)
    return DocumentEncryption.decrypt_content(encrypted_content, key)


class CryptoUtils:
    """Unified cryptographic utilities class."""
    
    def __init__(self):
        """Initialize crypto utilities."""
        self.hasher = DocumentHasher()
        self.encryption = DocumentEncryption()
        self.validator = IntegrityValidator()
        self.random = SecureRandom()
    
    def generate_key(self) -> bytes:
        """Generate a new encryption key."""
        return self.encryption.generate_key()
    
    def calculate_hash(self, content: Union[bytes, str], algorithm: str = 'sha256') -> str:
        """Calculate hash of content."""
        if algorithm == 'sha256':
            return self.hasher.generate_sha256(content)
        elif algorithm == 'sha512':
            return self.hasher.generate_sha512(content)
        elif algorithm == 'md5':
            return self.hasher.generate_md5(content)
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    def encrypt_data(self, data: Union[bytes, str], key: bytes) -> str:
        """Encrypt data and return base64 encoded result."""
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data
        
        encrypted_bytes = self.encryption.encrypt_content(data_bytes, key)
        return base64.b64encode(encrypted_bytes).decode('utf-8')
    
    def decrypt_data(self, encrypted_data: Union[bytes, str], key: bytes) -> str:
        """Decrypt base64 encoded data."""
        if isinstance(encrypted_data, str):
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        else:
            encrypted_bytes = encrypted_data
        
        decrypted_bytes = self.encryption.decrypt_content(encrypted_bytes, key)
        return decrypted_bytes.decode('utf-8')
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate secure random token."""
        return self.random.generate_token(length)
    
    def create_signature(self, content: Union[bytes, str], secret_key: str) -> str:
        """Create HMAC signature for content."""
        return self.validator.create_integrity_signature(content, secret_key)
    
    def verify_signature(self, content: Union[bytes, str], signature: str, secret_key: str) -> bool:
        """Verify HMAC signature."""
        return self.validator.verify_integrity_signature(content, signature, secret_key)
    
    def get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime
        return datetime.utcnow().isoformat()