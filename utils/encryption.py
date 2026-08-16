"""
Encryption utilities for config data storage.

Uses Fernet (symmetric encryption) to encrypt sensitive fields in cloud configs.
Non-sensitive fields remain in plaintext for queryability.
"""

import base64
import hashlib
import json
import logging
import os
import re

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Explicit allowlist of known sensitive fields, kept for documentation and for
# the __fields__ marker on already-encrypted rows.
_SENSITIVE_FIELDS = {
    "client_secret", "key_file_base64", "key_file_content",
    "aws_secret_access_key", "secret_access_key", "session_token", "external_id",
}

# Defensive backstop: any field whose name matches this pattern is treated as
# sensitive even if it isn't in the explicit allowlist above, so a future
# provider can't silently store a credential in plaintext by naming its field
# something we didn't anticipate (see audit doc P1-3).
_SENSITIVE_FIELD_PATTERN = re.compile(r"(secret|password|token|key)", re.IGNORECASE)


def _is_sensitive_field(name: str) -> bool:
    return name in _SENSITIVE_FIELDS or bool(_SENSITIVE_FIELD_PATTERN.search(name))


def get_encryption_key() -> bytes:
    """
    Get or derive encryption key from ENCRYPTION_KEY environment variable.

    If ENCRYPTION_KEY is set, it should be a base64-urlsafe 32-byte key.
    If not set or invalid, derive one from the default using SHA-256.

    Returns:
        bytes: Valid Fernet key (base64-urlsafe encoded).

    Raises:
        ValueError: If ENCRYPTION_KEY is not set or is the demo value.
    """
    env_key = os.getenv("ENCRYPTION_KEY")
    if not env_key:
        raise ValueError("ENCRYPTION_KEY environment variable is required")
    if env_key == "demo-key-change-in-production":
        raise ValueError("ENCRYPTION_KEY must be changed from demo value")

    # Try to use the env key as-is (assume it's already base64-urlsafe)
    try:
        # Validate it's a valid Fernet key
        Fernet(env_key.encode() if isinstance(env_key, str) else env_key)
        return env_key.encode() if isinstance(env_key, str) else env_key
    except Exception:
        logger.debug("ENCRYPTION_KEY not valid Fernet key, deriving")

    # Fallback: derive a valid key from the string using SHA-256
    hash_obj = hashlib.sha256(env_key.encode())
    derived = base64.urlsafe_b64encode(hash_obj.digest())
    return derived


def encrypt_config(config: dict) -> dict:
    """
    Encrypt sensitive fields in a config dict using Fernet.

    Sensitive fields: see _SENSITIVE_FIELDS, plus any field name matching
    _SENSITIVE_FIELD_PATTERN (secret/password/token/key, case-insensitive).
    Non-sensitive fields remain in plaintext for DB queryability.

    Args:
        config: Config dict, may contain sensitive data

    Returns:
        dict: Config with sensitive fields encrypted, tagged with __enc__ marker.
              If no sensitive fields, returns config as-is.
    """
    if not isinstance(config, dict):
        return config

    sensitive_field_names = [field for field in config if _is_sensitive_field(field)]

    if not sensitive_field_names:
        return config

    # Extract sensitive fields
    to_encrypt = {}
    encrypted_field_names = []
    for field in sensitive_field_names:
        to_encrypt[field] = config[field]
        encrypted_field_names.append(field)

    # Encrypt the sensitive data as JSON
    key = get_encryption_key()
    f = Fernet(key)
    plaintext = json.dumps(to_encrypt).encode()
    encrypted_token = f.encrypt(plaintext).decode()

    # Build result: non-sensitive fields + encrypted marker
    result = {k: v for k, v in config.items() if k not in sensitive_field_names}
    result["__enc__"] = True
    result["__data__"] = encrypted_token
    result["__fields__"] = encrypted_field_names

    return result


def decrypt_config(encrypted) -> dict:
    """
    Decrypt sensitive fields in a config dict, or return as-is if unencrypted.

    Handles three cases:
    1. Encrypted dict with __enc__ marker: decrypt __data__ field
    2. Plain dict (legacy): return as-is
    3. String (legacy base64): try to decode

    Args:
        encrypted: Config dict, encrypted dict, or legacy string format

    Returns:
        dict: Full config dict with sensitive fields decrypted.
    """
    if isinstance(encrypted, dict):
        # Check if it's encrypted
        if encrypted.get("__enc__") is True:
            try:
                key = get_encryption_key()
                f = Fernet(key)
                encrypted_token = encrypted["__data__"]
                plaintext = f.decrypt(encrypted_token.encode()).decode()
                decrypted_fields = json.loads(plaintext)

                # Merge back: non-sensitive + decrypted sensitive
                result = {k: v for k, v in encrypted.items()
                         if k not in ["__enc__", "__data__", "__fields__"]}
                result.update(decrypted_fields)
                return result
            except (InvalidToken, json.JSONDecodeError, Exception):
                # Decryption failed — log warning and return with sensitive fields redacted
                import logging
                logging.getLogger("encryption").warning(
                    "Failed to decrypt config data; returning with sensitive fields redacted"
                )
                return {k: v for k, v in encrypted.items()
                       if k not in ["__enc__", "__data__", "__fields__"]}
        else:
            # Plain dict, no encryption
            return encrypted

    # Handle legacy string formats
    if isinstance(encrypted, str):
        try:
            return json.loads(base64.b64decode(encrypted.encode()).decode())  # type: ignore[no-any-return]
        except Exception:
            try:
                return json.loads(encrypted)  # type: ignore[no-any-return]
            except Exception:
                return {}

    return encrypted if encrypted else {}
