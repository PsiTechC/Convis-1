"""
Encryption utilities for securing sensitive data like API credentials
"""
from cryptography.fernet import Fernet
from app.config.settings import settings
import logging
import base64

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""

    def __init__(self):
        if settings.encryption_key:
            try:
                # Ensure the key is properly formatted
                key = settings.encryption_key.encode() if isinstance(settings.encryption_key, str) else settings.encryption_key
                # Pad or truncate to 32 bytes for Fernet
                key = base64.urlsafe_b64encode(key[:32].ljust(32, b'='))
                self.cipher = Fernet(key)
                self.enabled = True
                logger.info("Encryption service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize encryption: {e}")
                self.cipher = None
                self.enabled = False
        else:
            logger.warning("No encryption key configured - credentials will be stored unencrypted")
            self.cipher = None
            self.enabled = False

    def encrypt(self, data: str) -> str:
        """
        Encrypt a string

        Args:
            data: Plain text string to encrypt

        Returns:
            Encrypted string (base64 encoded)
        """
        if not self.enabled or not self.cipher:
            logger.warning("Encryption not enabled - returning plain text")
            return data

        try:
            encrypted = self.cipher.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt a string

        Args:
            encrypted_data: Encrypted string (base64 encoded)

        Returns:
            Decrypted plain text string
        """
        if not self.enabled or not self.cipher:
            logger.warning("Encryption not enabled - returning data as-is")
            return encrypted_data

        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            # If decryption fails, might be plain text (backwards compatibility)
            logger.warning("Decryption failed - data might be plain text")
            return encrypted_data

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new encryption key

        Returns:
            Base64 encoded encryption key
        """
        key = Fernet.generate_key()
        return key.decode()


# Global encryption service instance
encryption_service = EncryptionService()
