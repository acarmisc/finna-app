"""Encryption utilities using Fernet (AES) from cryptography library."""

from __future__ import annotations

import base64
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

SENSITIVE_FIELDS = {"client_secret", "key_file_content", "service_account_key"}


def _get_encryption_key() -> bytes:
    """Get or generate encryption key from ENCRYPTION_KEY env var."""
    key_env = os.getenv("ENCRYPTION_KEY")
    if key_env:
        try:
            return base64.urlsafe_b64decode(key_env)
        except ValueError:
            pass
    key = Fernet.generate_key()
    os.environ["ENCRYPTION_KEY"] = base64.urlsafe_b64encode(key).decode()  # type: ignore
    return key


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
