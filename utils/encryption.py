"""
Encryption utilities for config data storage.
"""

import base64
import json
import os


def get_encryption_key() -> str:
    """Get encryption key from environment."""
    return os.getenv("ENCRYPTION_KEY", "demo-key-change-in-production")


def encrypt_config(config: dict) -> dict:
    """Return config dict for storage (encryption placeholder)."""
    return config


def decrypt_config(encrypted) -> dict:
    """Return config dict from storage, handling legacy base64-encoded values."""
    if isinstance(encrypted, dict):
        return encrypted
    if isinstance(encrypted, str):
        try:
            return json.loads(base64.b64decode(encrypted.encode()).decode())
        except Exception:
            return json.loads(encrypted)
    return encrypted
