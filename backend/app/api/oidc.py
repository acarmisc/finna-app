"""OIDC state/nonce storage for multi-replica deployments.

This module provides database-backed storage for OAuth2/OIDC state and nonce values,
enabling proper multi-replica support without requiring sticky sessions.

Key features:
- State/nonce stored in PostgreSQL for multi-replica support
- Automatic expiry cleanup for expired entries
- One-time state consumption to prevent replay attacks
- Thread-safe database operations via connection pool

To use this module, the `oidc_state` database table must be created first via migration.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Tuple
from uuid import UUID

from .db import execute, query_one  # Database functions for multi-replica support

logger = logging.getLogger("api.oidc")

# Configuration
STATE_EXPIRY = 600  # 10 minutes in seconds
STATE_LENGTH = 32   # Length of state parameter


def generate_state_and_nonce() -> Tuple[str, str]:
    """Generate a secure random state and nonce for OIDC flow.
    
    Returns:
        Tuple of (state, nonce) as strings
    """
    state = secrets.token_urlsafe(STATE_LENGTH)
    nonce = secrets.token_urlsafe(STATE_LENGTH)
    return state, nonce


def generate_code_verifier() -> str:
    """Generate a secure code verifier for PKCE.
    
    Returns:
        Code verifier string (43-128 characters)
    """
    return secrets.token_urlsafe(43)


def store_state(
    state: str,
    provider_id: UUID,
    nonce: str,
    code_verifier: str,
) -> None:
    """Store state and related values for validation during callback.
    
    Args:
        state: OAuth2 state parameter
        provider_id: UUID of the OIDC provider configuration
        nonce: OAuth2 nonce for ID token validation
        code_verifier: PKCE code verifier for token exchange
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=STATE_EXPIRY)
    
    execute(
        """
        INSERT INTO oidc_state (state, provider_id, nonce, code_verifier, expires_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (state, str(provider_id), nonce, code_verifier, expires_at),
    )


def validate_and_consume_state(state: str) -> Tuple[UUID, str, str]:
    """Validate state (CSRF check) and consume it (one-time use).
    
    Args:
        state: OAuth2 state parameter to validate
        
    Returns:
        Tuple of (provider_id, nonce, code_verifier)
        
    Raises:
        OIDCError: If state is invalid, expired, or already consumed
    """
    row = query_one(
        """
        SELECT provider_id, nonce, code_verifier, expires_at
        FROM oidc_state
        WHERE state = %s
        """,
        (state,),
    )
    
    if not row:
        raise OIDCError("Invalid or missing state")
    
    expires_at = row["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    
    now = datetime.now(timezone.utc)
    if now > expires_at:
        execute("DELETE FROM oidc_state WHERE state = %s", (state,))
        raise OIDCError("State expired")
    
    # Consume (one-time use) - delete the record
    execute("DELETE FROM oidc_state WHERE state = %s", (state,))
    
    return UUID(row["provider_id"]), row["nonce"], row["code_verifier"]


def clear_expired_states() -> int:
    """Remove expired state entries from storage.
    
    Returns:
        Number of entries removed
    """
    expired_count = query_one("SELECT COUNT(*) as count FROM oidc_state WHERE expires_at < now()")
    if expired_count:
        count = expired_count.get("count", 0)
        execute("DELETE FROM oidc_state WHERE expires_at < now()")
        return count
    return 0


def clear_all_states() -> int:
    """Remove all state entries from storage. Useful for testing.
    
    Returns:
        Number of entries removed
    """
    result = query_one("SELECT COUNT(*) as count FROM oidc_state")
    count = result.get("count", 0) if result else 0
    execute("DELETE FROM oidc_state")
    return count


class OIDCError(Exception):
    """Exception raised for OIDC operation errors."""
    pass
