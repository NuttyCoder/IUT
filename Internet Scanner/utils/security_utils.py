import hashlib
import secrets
import base64
from typing import Tuple, Optional
from cryptography.fernet import Fernet

class SecurityUtils:
    """
    Security utility functions for encryption and authentication
    """
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hash password with salt
        
        Args:
            password: Password to hash
            salt: Optional salt, generated if not provided
            
        Returns:
            Tuple of (hashed_password, salt)
        """
        if not salt:
            salt = secrets.token_hex(16)
        
        # Combine password and salt
        salted = password + salt
        # Create hash
        hashed = hashlib.sha256(salted.encode()).hexdigest()
        
        return hashed, salt
    
    @staticmethod
    def generate_key() -> bytes:
        """Generate encryption key"""
        return Fernet.generate_key()
    
    @staticmethod
    def encrypt_data(data: str, key: bytes) -> str:
        """
        Encrypt data using Fernet (symmetric encryption)
        
        Args:
            data: String to encrypt
            key: Encryption key
            
        Returns:
            Encrypted string
        """
        f = Fernet(key)
        encrypted = f.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    
    @staticmethod
    def decrypt_data(encrypted_data: str, key: bytes) -> str:
        """
        Decrypt data using Fernet
        
        Args:
            encrypted_data: Encrypted string
            key: Encryption key
            
        Returns:
            Decrypted string
        """
        f = Fernet(key)
        decrypted = f.decrypt(base64.b64decode(encrypted_data))
        return decrypted.decode()