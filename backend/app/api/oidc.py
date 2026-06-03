"""OIDC client for standards-compliant OpenID Connect flows.

Handles discovery, JWKS rotation, token exchange, and ID token validation.
Uses authlib for spec-compliant JWT handling and algorithm validation.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from jose import JWTError, jwt

logger = logging.getLogger("api.oidc")

# Cache for discovered metadata and JWKS
_discovery_cache: dict[str, tuple[dict[str, Any], float]] = {}
_jwks_cache: dict[str, tuple[dict[str, Any], float]] = {}

DISCOVERY_CACHE_TTL = 3600  # 1 hour
JWKS_CACHE_TTL = 300  # 5 minutes

# In-memory state/nonce storage (single-replica only; see OIDC-PLAN.md for multi-replica path)
_state_store: dict[str, dict[str, Any]] = {}
STATE_EXPIRY = 600  # 10 minutes


class OIDCError(Exception):
    """Base OIDC error."""
    pass


class ProviderMetadata(dict):
    """OIDC provider metadata from discovery."""
    pass


async def discover_provider(issuer: str) -> ProviderMetadata:
    """
    Discover OIDC provider metadata from issuer's .well-known endpoint.

    Args:
        issuer: Base issuer URL (e.g., https://keycloak.example.com/realms/finna)

    Returns:
        ProviderMetadata with authorization_endpoint, token_endpoint, jwks_uri, etc.

    Raises:
        OIDCError: If discovery fails or required endpoints missing.
    """
    issuer = issuer.rstrip("/")

    # Check cache
    if issuer in _discovery_cache:
        metadata, cached_at = _discovery_cache[issuer]
        if time.time() - cached_at < DISCOVERY_CACHE_TTL:
            logger.debug(f"Using cached discovery for {issuer}")
            return ProviderMetadata(metadata)

    discovery_url = f"{issuer}/.well-known/openid-configuration"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(discovery_url)
            response.raise_for_status()
            metadata = response.json()
    except httpx.RequestError as e:
        raise OIDCError(f"Discovery request failed: {e}")
    except httpx.HTTPStatusError as e:
        raise OIDCError(f"Discovery HTTP error: {e.response.status_code}")

    # Validate required endpoints
    required = {"authorization_endpoint", "token_endpoint", "jwks_uri"}
    missing = required - set(metadata.keys())
    if missing:
        raise OIDCError(f"Discovery metadata missing required endpoints: {missing}")

    # Cache
    _discovery_cache[issuer] = (metadata, time.time())

    return ProviderMetadata(metadata)


async def get_jwks(issuer: str) -> dict[str, Any]:
    """
    Fetch JWKS from provider's jwks_uri with caching.

    Args:
        issuer: Provider issuer URL

    Returns:
        JWKS dict with "keys" array.

    Raises:
        OIDCError: If fetch fails.
    """
    # Discover first (cached)
    metadata = await discover_provider(issuer)
    jwks_uri = metadata.get("jwks_uri", "")

    if not jwks_uri:
        raise OIDCError("No jwks_uri in provider metadata")

    # Check cache
    if jwks_uri in _jwks_cache:
        jwks, cached_at = _jwks_cache[jwks_uri]
        if time.time() - cached_at < JWKS_CACHE_TTL:
            logger.debug(f"Using cached JWKS for {jwks_uri}")
            return jwks

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(jwks_uri)
            response.raise_for_status()
            jwks = response.json()
    except httpx.RequestError as e:
        raise OIDCError(f"JWKS request failed: {e}")
    except httpx.HTTPStatusError as e:
        raise OIDCError(f"JWKS HTTP error: {e.response.status_code}")

    # Cache
    _jwks_cache[jwks_uri] = (jwks, time.time())

    return jwks


def build_authorization_url(
    provider_metadata: ProviderMetadata,
    client_id: str,
    redirect_uri: str,
    state: str,
    nonce: str,
    code_challenge: str,
    scopes: list[str] | None = None,
) -> str:
    """
    Build authorization URL with PKCE + state + nonce.

    Args:
        provider_metadata: From discover_provider()
        client_id: OIDC client ID
        redirect_uri: Callback URL
        state: Random state value (for CSRF protection, single-use)
        nonce: Random nonce (for ID token binding)
        code_challenge: PKCE S256 challenge
        scopes: List of scopes (default: openid profile email)

    Returns:
        Full authorization URL.
    """
    scopes = scopes or ["openid", "profile", "email"]
    auth_url = provider_metadata.get("authorization_endpoint", "")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    from urllib.parse import urlencode
    return f"{auth_url}?{urlencode(params)}"


async def exchange_code(
    provider_metadata: ProviderMetadata,
    client_id: str,
    client_secret: str,
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> dict[str, Any]:
    """
    Exchange authorization code for tokens.

    Args:
        provider_metadata: From discover_provider()
        client_id: OIDC client ID
        client_secret: OIDC client secret
        code: Authorization code from callback
        code_verifier: PKCE verifier (plaintext, will be S256-hashed)
        redirect_uri: Callback URL (must match original)

    Returns:
        {"access_token": "...", "id_token": "...", ...}

    Raises:
        OIDCError: If token exchange fails.
    """
    token_url = provider_metadata.get("token_endpoint", "")

    if not token_url:
        raise OIDCError("No token_endpoint in provider metadata")

    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(token_url, data=payload)
            response.raise_for_status()
            tokens = response.json()
    except httpx.RequestError as e:
        raise OIDCError(f"Token exchange request failed: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"Token exchange HTTP error: {e.response.status_code} {e.response.text}")
        raise OIDCError(f"Token exchange failed: {e.response.status_code}")

    return tokens


async def verify_id_token(
    id_token: str,
    provider_metadata: ProviderMetadata,
    client_id: str,
    nonce: str,
) -> dict[str, Any]:
    """
    Verify ID token signature, claims, and nonce binding.

    Security checks (all non-negotiable):
    - Valid signature (RS*/ES* only, no HS*, no alg:none)
    - iss matches issuer exactly
    - aud contains client_id
    - exp not expired
    - iat not far in future (<=5 min skew allowed)
    - nonce matches exactly

    Args:
        id_token: Signed JWT from token_endpoint
        provider_metadata: From discover_provider()
        client_id: OIDC client ID
        nonce: Expected nonce value (from state store)

    Returns:
        Decoded and validated claims dict.

    Raises:
        OIDCError: If validation fails.
    """
    issuer = provider_metadata.get("issuer", "")

    if not issuer:
        raise OIDCError("Provider metadata missing issuer")

    # Get JWKS
    jwks = await get_jwks(issuer)
    keys = jwks.get("keys", [])

    if not keys:
        raise OIDCError("JWKS has no keys")

    # Decode header to get kid
    try:
        header = jwt.get_unverified_header(id_token)
    except JWTError as e:
        raise OIDCError(f"Invalid token format: {e}")

    kid = header.get("kid")
    alg = header.get("alg", "")

    # Reject alg:none and HS*
    if alg == "none" or alg.startswith("HS"):
        raise OIDCError(f"Insecure algorithm not allowed: {alg}")

    # Find the key
    key = None
    for k in keys:
        if k.get("kid") == kid:
            key = k
            break

    if not key:
        if kid:
            logger.warning(f"JWKS kid {kid} not found, trying all keys (kid rotation?)")
        # Try all keys if kid not found
        if not keys:
            raise OIDCError("No keys in JWKS to verify with")
        # Try first RS*/ES* key
        for k in keys:
            k_alg = k.get("alg", "")
            if k_alg.startswith("RS") or k_alg.startswith("ES"):
                key = k
                break

    if not key:
        raise OIDCError("No suitable key found in JWKS")

    # Verify signature
    try:
        claims = jwt.decode(id_token, key, algorithms=[alg], options={"verify_signature": True})
    except JWTError as e:
        raise OIDCError(f"Signature verification failed: {e}")

    # Validate claims
    now = datetime.now(timezone.utc).timestamp()

    # exp check
    exp = claims.get("exp")
    if not exp or exp < now:
        raise OIDCError("ID token expired")

    # iat check (allow 5 min skew for clock drift)
    iat = claims.get("iat")
    if iat and iat > now + 300:
        raise OIDCError("ID token iat in future (clock skew > 5 min?)")

    # iss check
    token_iss = claims.get("iss", "")
    if token_iss != issuer:
        raise OIDCError(f"Issuer mismatch: {token_iss} != {issuer}")

    # aud check
    aud = claims.get("aud")
    if isinstance(aud, list):
        if client_id not in aud:
            raise OIDCError(f"Client ID {client_id} not in aud: {aud}")
    else:
        if aud != client_id:
            raise OIDCError(f"Audience mismatch: {aud} != {client_id}")

    # nonce check
    token_nonce = claims.get("nonce", "")
    if token_nonce != nonce:
        raise OIDCError(f"Nonce mismatch: {token_nonce} != {nonce}")

    return claims


def generate_pkce_pair() -> tuple[str, str]:
    """
    Generate PKCE code_verifier and code_challenge (S256).

    Returns:
        (code_verifier, code_challenge)
    """
    code_verifier = secrets.token_urlsafe(32)  # 43 chars, 256 bits entropy
    code_challenge = (
        hashlib.sha256(code_verifier.encode()).digest()
    )
    from base64 import urlsafe_b64encode
    code_challenge_b64 = urlsafe_b64encode(code_challenge).decode().rstrip("=")
    return code_verifier, code_challenge_b64


def generate_state_and_nonce() -> tuple[str, str]:
    """Generate random state and nonce values."""
    return secrets.token_urlsafe(32), secrets.token_urlsafe(32)


def store_state(state: str, provider_id: UUID, nonce: str, code_verifier: str) -> None:
    """
    Store state and related values for validation during callback.

    Args:
        state: Random CSRF state
        provider_id: OIDC provider UUID
        nonce: Random nonce for ID token binding
        code_verifier: PKCE verifier (plaintext)
    """
    _state_store[state] = {
        "provider_id": str(provider_id),
        "nonce": nonce,
        "code_verifier": code_verifier,
        "expires_at": time.time() + STATE_EXPIRY,
    }


def validate_and_consume_state(state: str) -> tuple[str, str, str]:
    """
    Validate state (CSRF check) and consume it (one-time use).

    Args:
        state: State value from callback query string

    Returns:
        (provider_id, nonce, code_verifier)

    Raises:
        OIDCError: If state invalid, expired, or already consumed.
    """
    if not state or state not in _state_store:
        raise OIDCError("Invalid or missing state")

    stored = _state_store[state]

    # Check expiry
    if time.time() > stored["expires_at"]:
        _state_store.pop(state, None)
        raise OIDCError("State expired")

    # Consume (one-time use)
    _state_store.pop(state)

    return stored["provider_id"], stored["nonce"], stored["code_verifier"]


def clear_expired_states() -> None:
    """Remove expired state entries (can be called periodically by cleanup job)."""
    now = time.time()
    expired = [s for s, v in _state_store.items() if v["expires_at"] < now]
    for s in expired:
        _state_store.pop(s, None)
    if expired:
        logger.info(f"Cleared {len(expired)} expired OIDC states")
