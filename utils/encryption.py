"""Encryption utilities using Fernet (AES) from cryptography library."""

from __future__ import annotations

import base64
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

SENSITIVE_FIELDS = {"client_secret", "key_file_content", "service_account_key"}


def _get_encryption_key() -> str:
    """Get or generate encryption key from ENCRYPTION_KEY env var.

    Returns the base64-encoded key string (which Fernet will decode).
    """
    key_env = os.getenv("ENCRYPTION_KEY")
    if key_env:
        return key_env
    key = Fernet.generate_key()
    # key is bytes, but contains base64-encoded ASCII
    key_str = key.decode()
    os.environ["ENCRYPTION_KEY"] = key_str  # type: ignore
    return key_str


_fernet = Fernet(_get_encryption_key())


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string."""
    if not plaintext:
        return plaintext
    if isinstance(plaintext, str):
        plaintext_bytes = plaintext.encode()
    else:
        plaintext_bytes = plaintext
    ciphertext = _fernet.encrypt(plaintext_bytes)
    return base64.urlsafe_b64encode(ciphertext).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a ciphertext string."""
    if not ciphertext:
        return ciphertext
    try:
        data = base64.urlsafe_b64decode(ciphertext.encode())
        return _fernet.decrypt(data).decode()
    except (InvalidToken, ValueError):
        return ciphertext


def encrypt_config(config: dict[str, Any]) -> dict[str, Any]:
    """Encrypt sensitive fields in a config dict."""
    encrypted = config.copy()
    for field in SENSITIVE_FIELDS:
        if field in encrypted and encrypted[field]:
            value = encrypted[field]
            if isinstance(value, str):
                encrypted[field] = encrypt(value)
            elif isinstance(value, dict):
                encrypted[field] = encrypt_config(value)
    return encrypted


def decrypt_config(config: dict[str, Any]) -> dict[str, Any]:
    """Decrypt sensitive fields in a config dict."""
    decrypted = config.copy()
    for field in SENSITIVE_FIELDS:
        if field in decrypted and decrypted[field]:
            value = decrypted[field]
            if isinstance(value, str):
                decrypted[field] = decrypt(value)
            elif isinstance(value, dict):
                decrypted[field] = decrypt_config(value)
    return decrypted
