"""
Encryption utilities for config data storage.
"""

import base64
import json
import os


def get_encryption_key() -> str:
    """Get encryption key from environment."""
    return os.getenv("ENCRYPTION_KEY", "demo-key-change-in-production")


def encrypt_config(config: dict) -> str:
    """Encrypt a config dict for storage (simple base64 for demo)."""
    return base64.b64encode(json.dumps(config).encode()).decode()


def decrypt_config(encrypted: str | dict) -> dict:
    """Decrypt an encrypted config string, or return dict as-is."""
    if isinstance(encrypted, dict):
        return encrypted
    return json.loads(base64.b64decode(encrypted.encode()).decode())
