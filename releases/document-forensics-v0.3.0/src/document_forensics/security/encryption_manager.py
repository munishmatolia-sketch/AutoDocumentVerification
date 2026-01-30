"""Data encryption manager for at-rest and in-transit encryption."""

import os
import base64
from typing import Dict, Any, Optional, Union
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..utils.crypto import CryptoUtils


class EncryptionManager:
    """Manages data encryption at rest and in transit."""
    
    def __init__(self, key_directory: str = "keys"):
        """
        Initialize the encryption manager.
        
        Args:
            key_directory: Directory to store encryption keys
        """
        self.key_directory = Path(key_directory)
        self.key_directory.mkdir(parents=True, exist_ok=True)
        
        self.crypto_utils = CryptoUtils()
        
        # Initialize symmetric encryption key
        self.symmetric_key_file = self.key_directory / "symmetric.key"
        self.symmetric_key = self._load_or_generate_symmetric_key()
        
        # Initialize asymmetric key pair
        self.private_key_file = self.key_directory / "private.pem"
        self.public_key_file = self.key_directory / "public.pem"
        self.private_key, self.public_key = self._load_or_generate_asymmetric_keys()
        
        # Fernet instance for symmetric encryption
        self.fernet = Fernet(self.symmetric_key)
    
    def _load_or_generate_symmetric_key(self) -> bytes:
        """Load existing symmetric key or generate new one."""
        if self.symmetric_key_file.exists():
            with open(self.symmetric_key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.symmetric_key_file, 'wb') as f:
                f.write(key)
            return key
    
    def _load_or_generate_asymmetric_keys(self):
        """Load existing asymmetric keys or generate new pair."""
        if self.private_key_file.exists() and self.public_key_file.exists():
            # Load existing keys
            with open(self.private_key_file, 'rb') as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None
                )
            
            with open(self.public_key_file, 'rb') as f:
                public_key = serialization.load_pem_public_key(f.read())
            
            return private_key, public_key
        
        else:
            # Generate new key pair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            public_key = private_key.public_key()
            
            # Save private key
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open(self.private_key_file, 'wb') as f:
                f.write(private_pem)
            
            # Save public key
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            with open(self.public_key_file, 'wb') as f:
                f.write(public_pem)
            
            return private_key, public_key
    
    def encrypt_data_symmetric(self, data: Union[str, bytes]) -> str:
        """
        Encrypt data using symmetric encryption.
        
        Args:
            data: Data to encrypt
            
        Returns:
            Base64 encoded encrypted data
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        encrypted_data = self.fernet.encrypt(data)
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt_data_symmetric(self, encrypted_data: str) -> bytes:
        """
        Decrypt data using symmetric encryption.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Decrypted data as bytes
        """
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        return self.fernet.decrypt(encrypted_bytes)
    
    def encrypt_data_asymmetric(self, data: Union[str, bytes], public_key=None) -> str:
        """
        Encrypt data using asymmetric encryption.
        
        Args:
            data: Data to encrypt (limited size due to RSA constraints)
            public_key: Optional public key to use (defaults to instance key)
            
        Returns:
            Base64 encoded encrypted data
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        key_to_use = public_key or self.public_key
        
        # RSA can only encrypt limited data size
        max_size = key_to_use.key_size // 8 - 2 * hashes.SHA256.digest_size - 2
        if len(data) > max_size:
            raise ValueError(f"Data too large for RSA encryption. Max size: {max_size} bytes")
        
        encrypted_data = key_to_use.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt_data_asymmetric(self, encrypted_data: str, private_key=None) -> bytes:
        """
        Decrypt data using asymmetric encryption.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            private_key: Optional private key to use (defaults to instance key)
            
        Returns:
            Decrypted data as bytes
        """
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        key_to_use = private_key or self.private_key
        
        decrypted_data = key_to_use.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return decrypted_data
    
    def encrypt_file(self, file_path: str, output_path: Optional[str] = None) -> str:
        """
        Encrypt a file using symmetric encryption.
        
        Args:
            file_path: Path to file to encrypt
            output_path: Optional output path (defaults to input + .enc)
            
        Returns:
            Path to encrypted file
        """
        input_path = Path(file_path)
        if not input_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if output_path is None:
            output_path = str(input_path) + ".enc"
        
        # Read and encrypt file
        with open(input_path, 'rb') as f:
            file_data = f.read()
        
        encrypted_data = self.fernet.encrypt(file_data)
        
        # Write encrypted file
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)
        
        return output_path
    
    def decrypt_file(self, encrypted_file_path: str, output_path: Optional[str] = None) -> str:
        """
        Decrypt a file using symmetric encryption.
        
        Args:
            encrypted_file_path: Path to encrypted file
            output_path: Optional output path (defaults to input without .enc)
            
        Returns:
            Path to decrypted file
        """
        input_path = Path(encrypted_file_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Encrypted file not found: {encrypted_file_path}")
        
        if output_path is None:
            if str(input_path).endswith('.enc'):
                output_path = str(input_path)[:-4]  # Remove .enc extension
            else:
                output_path = str(input_path) + ".dec"
        
        # Read and decrypt file
        with open(input_path, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted_data = self.fernet.decrypt(encrypted_data)
        
        # Write decrypted file
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)
        
        return output_path
    
    def encrypt_document_metadata(self, metadata: Dict[str, Any]) -> str:
        """
        Encrypt document metadata for secure storage.
        
        Args:
            metadata: Metadata dictionary to encrypt
            
        Returns:
            Encrypted metadata as base64 string
        """
        import json
        metadata_json = json.dumps(metadata, default=str)
        return self.encrypt_data_symmetric(metadata_json)
    
    def decrypt_document_metadata(self, encrypted_metadata: str) -> Dict[str, Any]:
        """
        Decrypt document metadata.
        
        Args:
            encrypted_metadata: Encrypted metadata as base64 string
            
        Returns:
            Decrypted metadata dictionary
        """
        import json
        decrypted_json = self.decrypt_data_symmetric(encrypted_metadata)
        return json.loads(decrypted_json.decode('utf-8'))
    
    def generate_secure_token(self, length: int = 32) -> str:
        """
        Generate a secure random token.
        
        Args:
            length: Token length in bytes
            
        Returns:
            Base64 encoded secure token
        """
        token_bytes = os.urandom(length)
        return base64.urlsafe_b64encode(token_bytes).decode('utf-8')
    
    def derive_key_from_password(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: Password to derive key from
            salt: Optional salt (generates random if not provided)
            
        Returns:
            Derived key bytes
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        return kdf.derive(password.encode('utf-8'))
    
    def get_public_key_pem(self) -> str:
        """Get public key in PEM format for sharing."""
        public_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return public_pem.decode('utf-8')
    
    def load_public_key_from_pem(self, pem_data: str):
        """Load public key from PEM format."""
        return serialization.load_pem_public_key(pem_data.encode('utf-8'))
    
    def create_encrypted_backup(self, data: Dict[str, Any], backup_path: str) -> None:
        """
        Create encrypted backup of data.
        
        Args:
            data: Data to backup
            backup_path: Path for backup file
        """
        import json
        
        # Serialize data
        data_json = json.dumps(data, default=str, indent=2)
        
        # Encrypt data
        encrypted_data = self.encrypt_data_symmetric(data_json)
        
        # Add metadata
        backup_metadata = {
            "created_at": self.crypto_utils.get_current_timestamp(),
            "encryption_method": "symmetric",
            "data": encrypted_data
        }
        
        # Write backup
        with open(backup_path, 'w') as f:
            json.dump(backup_metadata, f, indent=2)
    
    def restore_encrypted_backup(self, backup_path: str) -> Dict[str, Any]:
        """
        Restore data from encrypted backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            Restored data
        """
        import json
        
        # Read backup
        with open(backup_path, 'r') as f:
            backup_metadata = json.load(f)
        
        # Decrypt data
        encrypted_data = backup_metadata["data"]
        decrypted_json = self.decrypt_data_symmetric(encrypted_data)
        
        return json.loads(decrypted_json.decode('utf-8'))
    
    def get_encryption_status(self) -> Dict[str, Any]:
        """Get current encryption configuration status."""
        return {
            "symmetric_key_exists": self.symmetric_key_file.exists(),
            "asymmetric_keys_exist": (
                self.private_key_file.exists() and 
                self.public_key_file.exists()
            ),
            "key_directory": str(self.key_directory),
            "public_key_fingerprint": self.crypto_utils.calculate_hash(
                self.get_public_key_pem().encode()
            )[:16]
        }