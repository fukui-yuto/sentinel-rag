"""Encryption utilities for sensitive data (API keys, etc.)."""

import base64

from cryptography.fernet import Fernet

from src.core.config import settings


def _get_fernet() -> Fernet:
    """Derive a Fernet key from the application secret key."""
    import hashlib

    key = hashlib.sha256(settings.secret_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)


def encrypt_value(plaintext: str) -> bytes:
    """Encrypt a string value. Returns encrypted bytes."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8"))


def decrypt_value(ciphertext: bytes) -> str:
    """Decrypt bytes back to string."""
    f = _get_fernet()
    return f.decrypt(ciphertext).decode("utf-8")
