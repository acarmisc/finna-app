"""OIDC client for standards-compliant OpenID Connect flows.

Handles discovery, JWKS rotation, token exchange, and ID token validation.
Uses authlib for spec-compliant JWT handling and algorithm validation.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID

import httpx
from jose import JWTError, jwt
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

# Import metrics lazily to avoid circular import issues
# (metrics imports oidc for type hints, oidc imports metrics for metrics)

logger = logging.getLogger("api.oidc")

# =============== Circuit Breaker State ===============


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, trips after failures
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for external JWKS/Discovery calls."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for recovery from OPEN to HALF_OPEN."""
        if self._state == CircuitState.OPEN and self._last_failure_time is not None:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.debug("Circuit breaker transitioning to HALF_OPEN for testing recovery")
        return self._state

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.debug("Circuit breaker CLOSED after successful recovery test")
        else:
            self._failure_count = 0  # Reset on success in CLOSED state

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Failed during recovery test, go back to OPEN
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker OPENED again after failed recovery test")
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.error(f"Circuit breaker OPENED after {self._failure_count} failures")

    def is_available(self) -> bool:
        """Check if the circuit allows calls."""
        return self.state != CircuitState.OPEN


# =============== Circuit Breaker for Discovery ===============

_discovery_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
_jwks_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)


# =============== Stale Cache ===============

# Cache for discovered metadata and JWKS
_discovery_cache: dict[str, tuple[dict[str, Any], float]] = {}
_jwks_cache: dict[str, tuple[dict[str, Any], float]] = {}

# Stale cache for fallback when external fetch fails (kept much longer than normal cache)
_discovery_cache_stale: dict[str, tuple[dict[str, Any], float]] = {}
_jwks_cache_stale: dict[str, tuple[dict[str, Any], float]] = {}

DISCOVERY_CACHE_TTL = 3600  # 1 hour
JWKS_CACHE_TTL = 300  # 5 minutes
JWKS_STALE_TTL = 3600  # 1 hour - maximum age for stale cache fallback (extended from expiry)


# =============== In-Memory State Storage ===============

# In-memory state/nonce storage (for single-replica deployments, deprecated)
# Kept for backward compatibility during migration, but not used when DB pool is available
_state_store: dict[str, dict[str, Any]] = {}
STATE_EXPIRY = 600  # 10 minutes


class OIDCError(Exception):
    """Base OIDC error."""

    pass


class ProviderMetadata(dict):
    """OIDC provider metadata from discovery."""

    pass


# =============== Helper Functions ===============


def update_circuit_breaker_metrics() -> None:
    """Update Prometheus metrics for circuit breaker states."""
    try:
        from . import metrics
    except ImportError:
        return  # Metrics not available, skip updating

    for service, cb in [
        ("discovery", _discovery_circuit_breaker),
        ("jwks", _jwks_circuit_breaker),
    ]:
        state = cb.state.value
        state_value = {"closed": 0, "half_open": 0.5, "open": 1}.get(state, 0)
        metrics.oidc_circuit_breaker_state.labels(service=service).set(state_value)
        metrics.oidc_circuit_breaker_failures.labels(service=service).inc(cb._failure_count)


async def _fetch_with_backoff_and_cb(
    url: str,
    circuit_breaker: CircuitBreaker,
    method: str = "GET",
    **http_kwargs: Any,
) -> httpx.Response:
    """
    Fetch URL with exponential backoff and circuit breaker support.

    Args:
        url: URL to fetch
        circuit_breaker: CircuitBreaker instance
        method: HTTP method
        **http_kwargs: Additional httpx.AsyncClient kwargs

    Returns:
        httpx.Response on success

    Raises:
        OIDCError: If fetch fails after retries and circuit breaker is open
    """
    max_delay = 30.0  # Maximum delay between retries
    base_delay = 0.5  # Starting delay

    # Check circuit breaker first
    if not circuit_breaker.is_available():
        logger.warning(f"Circuit breaker OPEN for {url}, using stale cache if available")

    delay = base_delay
    last_error: Optional[Exception] = None

    for attempt in range(1, 4):  # Try up to 3 times
        # Check circuit breaker before each attempt
        if not circuit_breaker.is_available():
            logger.warning(f"Circuit breaker OPEN, skipping attempt {attempt} for {url}")
            break

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                if method == "GET":
                    response = await client.get(url, **http_kwargs)
                elif method == "POST":
                    response = await client.post(url, **http_kwargs)
                response.raise_for_status()

                # Record success in circuit breaker
                circuit_breaker.record_success()

                # If circuit was HALF_OPEN, this success helps close it
                if circuit_breaker.state == CircuitState.HALF_OPEN:
                    logger.info(f"Circuit breaker HALF_OPEN -> CLOSED for {url}")

                return response

        except httpx.RequestError as e:
            last_error = e
            logger.warning(f"Request attempt {attempt}/3 failed for {url}: {e}")
            circuit_breaker.record_failure()

            # Wait with exponential backoff (but don't wait if circuit is open)
            if attempt < 3 and circuit_breaker.is_available():
                await _sleep_with_backoff(delay)
                delay = min(delay * 2, max_delay)

        except httpx.HTTPStatusError as e:
            last_error = e
            logger.warning(f"HTTP error on attempt {attempt}/3 for {url}: {e}")
            circuit_breaker.record_failure()

            if attempt < 3 and circuit_breaker.is_available():
                await _sleep_with_backoff(delay)
                delay = min(delay * 2, max_delay)

    # All retries exhausted
    if last_error:
        raise OIDCError(f"Request to {url} failed after retries: {last_error}")


async def _sleep_with_backoff(delay: float) -> None:
    """Sleep with exponential backoff (non-blocking for async)."""
    import asyncio

    await asyncio.sleep(delay)


async def _discover_with_cache(
    issuer: str,
    circuit_breaker: CircuitBreaker,
    use_stale_if_no_new: bool = True,
) -> tuple[ProviderMetadata, bool]:
    """
    Discover provider metadata with caching and stale-cache fallback.

    Args:
        issuer: Base issuer URL
        circuit_breaker: CircuitBreaker instance
        use_stale_if_no_new: If True, use stale cache when new fetch fails

    Returns:
        (ProviderMetadata, was_stale: bool) - was_stale indicates if stale cache was used
    """
    # Import metrics lazily
    from . import metrics

    issuer = issuer.rstrip("/")

    # Check fresh cache first
    if issuer in _discovery_cache:
        metadata, cached_at = _discovery_cache[issuer]
        if time.time() - cached_at < DISCOVERY_CACHE_TTL:
            logger.debug(f"Using cached discovery for {issuer}")
            return ProviderMetadata(metadata), False

    discovery_url = f"{issuer}/.well-known/openid-configuration"

    # Try fresh fetch
    try:
        response = await _fetch_with_backoff_and_cb(discovery_url, circuit_breaker)
        metadata = response.json()
    except OIDCError as e:
        logger.warning(f"Discovery fetch failed for {issuer}: {e}")

        # Fall back to stale cache if available and enabled
        if use_stale_if_no_new and issuer in _discovery_cache_stale:
            metadata, cached_at = _discovery_cache_stale[issuer]
            age = time.time() - cached_at
            if age < JWKS_STALE_TTL:
                logger.warning(f"Using STALE discovery fallback for {issuer} (age: {age:.0f}s)")
                metrics.oidc_discovery_fallback_total.inc()
                return ProviderMetadata(metadata), True
            else:
                logger.warning(f"Stale discovery for {issuer} expired ({age:.0f}s > {JWKS_STALE_TTL}s)")

        # Re-raise the original error
        raise

    # Validate required endpoints
    required = {"authorization_endpoint", "token_endpoint", "jwks_uri"}
    missing = required - set(metadata.keys())
    if missing:
        if use_stale_if_no_new:
            logger.warning(f"Missing required endpoints: {missing}, using stale cache")
            if issuer in _discovery_cache_stale:
                metadata, _ = _discovery_cache_stale[issuer]
                metrics.oidc_discovery_fallback_total.inc()
                return ProviderMetadata(metadata), True
        raise OIDCError(f"Discovery metadata missing required endpoints: {missing}")

    # Update fresh cache
    _discovery_cache[issuer] = (metadata, time.time())

    # Keep track of stale cache (for later fallback)
    if issuer in _discovery_cache_stale:
        stale_metadata, stale_at = _discovery_cache_stale[issuer]
        if time.time() - stale_at < JWKS_STALE_TTL and stale_metadata.get("authorization_endpoint"):
            # Keep stale if not too old
            pass

    return ProviderMetadata(metadata), False


async def _get_jwks_with_cache(
    issuer: str,
    jwks_uri: str,
    circuit_breaker: CircuitBreaker,
    use_stale_if_no_new: bool = True,
) -> tuple[dict[str, Any], bool]:
    """
    Fetch JWKS with caching and stale-cache fallback.

    Args:
        issuer: Provider issuer URL
        jwks_uri: JWKS endpoint URI
        circuit_breaker: CircuitBreaker instance
        use_stale_if_no_new: If True, use stale cache when new fetch fails

    Returns:
        (jwks dict, was_stale: bool) - was_stale indicates if stale cache was used
    """
    # Import metrics lazily
    from . import metrics

    # Check fresh cache first
    if jwks_uri in _jwks_cache:
        jwks, cached_at = _jwks_cache[jwks_uri]
        if time.time() - cached_at < JWKS_CACHE_TTL:
            logger.debug(f"Using cached JWKS for {jwks_uri}")
            return jwks, False

    # Try fresh fetch
    try:
        response = await _fetch_with_backoff_and_cb(jwks_uri, circuit_breaker)
        jwks = response.json()
    except OIDCError as e:
        logger.warning(f"JWKS fetch failed for {jwks_uri}: {e}")

        # Fall back to stale cache if available and enabled
        if use_stale_if_no_new and jwks_uri in _jwks_cache_stale:
            jwks, cached_at = _jwks_cache_stale[jwks_uri]
            age = time.time() - cached_at
            if age < JWKS_STALE_TTL:
                logger.warning(f"Using STALE JWKS fallback for {jwks_uri} (age: {age:.0f}s)")
                metrics.oidc_jwks_fallback_total.inc()
                return jwks, True
            else:
                logger.warning(f"Stale JWKS for {jwks_uri} expired ({age:.0f}s > {JWKS_STALE_TTL}s)")

        # Re-raise the original error
        raise

    # Update fresh cache
    _jwks_cache[jwks_uri] = (jwks, time.time())

    return jwks, False


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
    result, _ = await _discover_with_cache(issuer, _discovery_circuit_breaker)
    return result


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

    jwks, _ = await _get_jwks_with_cache(issuer, jwks_uri, _jwks_circuit_breaker)
    return jwks


async def discover_provider_with_fallback(issuer: str) -> tuple[ProviderMetadata, bool]:
    """
    Discover provider with stale-cache fallback support.

    Returns (ProviderMetadata, was_stale) where was_stale is True if fallback was used.
    """
    result, was_stale = await _discover_with_cache(issuer, _discovery_circuit_breaker)
    return result, was_stale


async def get_jwks_with_fallback(issuer: str) -> tuple[dict[str, Any], bool]:
    """
    Get JWKS with stale-cache fallback support.

    Returns (jwks dict, was_stale) where was_stale is True if fallback was used.
    """
    metadata = await _discover_with_cache(issuer, _jwks_circuit_breaker, use_stale_if_no_new=True)
    jwks_uri = metadata[0].get("jwks_uri", "")

    if not jwks_uri:
        raise OIDCError("No jwks_uri in provider metadata")

    jwks, was_stale = await _get_jwks_with_cache(issuer, jwks_uri, _jwks_circuit_breaker)
    return jwks, was_stale


# =============== Original Functions (with circuit breaker) ===============


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
        {"access_token": "***", "id_token": "...", ...}

    Raises:
        OIDCError: If token exchange fails.
    """
    token_url = provider_metadata.get("token_endpoint", "")

    if not token_url:
        raise OIDCError("No token_endpoint in provider metadata")

    try:
        response = await _fetch_with_backoff_and_cb(
            token_url,
            _jwks_circuit_breaker,  # Reuse JWKS circuit breaker
            method="POST",
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
        )
        tokens = response.json()
    except OIDCError as e:
        raise OIDCError(f"Token exchange failed: {e}")

    # Don't use circuit breaker for token exchange success - exchange is different
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

    # Get JWKS (with fallback support)
    try:
        jwks, _ = await get_jwks_with_fallback(issuer)
    except OIDCError as e:
        logger.error(f"Failed to fetch JWKS for verification: {e}")
        raise OIDCError(f"Token verification failed: {e}")

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
    code_challenge = hashlib.sha256(code_verifier.encode()).digest()
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
        logger.info(f"Cleared {len(expired)} expired OIDC states (in-memory fallback)")


# ============================================================================
# Database-backed state storage (for multi-replica deployments)
# ============================================================================


async def store_state_async(
    state: str, provider_id: UUID, nonce: str, code_verifier: str, pool: AsyncConnectionPool | None = None
) -> None:
    """
    Store state and related values in PostgreSQL for multi-replica support.

    Args:
        state: Random CSRF state
        provider_id: OIDC provider UUID
        nonce: Random nonce for ID token binding
        code_verifier: PKCE verifier (plaintext)
        pool: AsyncConnectionPool (optional, uses default if not provided)
    """
    if pool is None:
        from ..db import get_async_pool

        pool = await get_async_pool()

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=STATE_EXPIRY)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO oidc_states (state, provider_id, nonce, code_verifier, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (state) DO UPDATE SET
                    provider_id = EXCLUDED.provider_id,
                    nonce = EXCLUDED.nonce,
                    code_verifier = EXCLUDED.code_verifier,
                    expires_at = EXCLUDED.expires_at,
                    created_at = now()
                """,
                (state, str(provider_id), nonce, code_verifier, expires_at),
            )
        await conn.commit()


async def validate_and_consume_state_async(state: str, pool: AsyncConnectionPool | None = None) -> tuple[str, str, str]:
    """
    Validate state (CSRF check) and consume it (one-time use) from PostgreSQL.

    Args:
        state: State value from callback query string
        pool: AsyncConnectionPool (optional, uses default if not provided)

    Returns:
        (provider_id, nonce, code_verifier)

    Raises:
        OIDCError: If state invalid, expired, or already consumed.
    """
    if pool is None:
        from ..db import get_async_pool

        pool = await get_async_pool()

    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            # Delete and return the row in one operation (atomic consume)
            await cur.execute(
                """
                DELETE FROM oidc_states
                WHERE state = %s AND expires_at > now()
                RETURNING state, provider_id, nonce, code_verifier, expires_at
                """,
                (state,),
            )
            row = await cur.fetchone()

    if not row:
        raise OIDCError("Invalid or missing state")

    return row["provider_id"], row["nonce"], row["code_verifier"]


async def clear_expired_states_async(pool: AsyncConnectionPool | None = None) -> int:
    """
    Remove expired state entries from PostgreSQL.

    Args:
        pool: AsyncConnectionPool (optional, uses default if not provided)

    Returns:
        Number of expired states cleared
    """
    if pool is None:
        from ..db import get_async_pool

        pool = await get_async_pool()

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                DELETE FROM oidc_states
                WHERE expires_at < now()
                RETURNING state
                """
            )
            rows = await cur.fetchall()

    if rows:
        deleted_count = len(rows)
        logger.info(f"Cleared {deleted_count} expired OIDC states (database)")
        return deleted_count
    return 0
