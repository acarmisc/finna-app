"""Tests for OIDC client module."""

import base64
import hashlib
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

from backend.app.api import oidc
from backend.app.api.oidc import OIDCError


@pytest.fixture
def rsa_keypair():
    """Generate ephemeral RSA keypair for test ID tokens."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    # Export as PEM
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # JWK format
    e = public_key.public_numbers().e
    n = public_key.public_numbers().n

    jwk = {
        "kty": "RSA",
        "kid": "test-key-1",
        "use": "sig",
        "alg": "RS256",
        "n": base64.urlsafe_b64encode(n.to_bytes(256, "big")).decode().rstrip("="),
        "e": base64.urlsafe_b64encode(e.to_bytes(3, "big")).decode().rstrip("="),
    }

    return {
        "private_key": private_key,
        "public_key": public_key,
        "private_pem": private_pem,
        "public_pem": public_pem,
        "jwk": jwk,
    }


@pytest.fixture
def mock_provider_metadata():
    """Standard OIDC provider metadata."""
    return {
        "issuer": "https://keycloak.example.com/realms/test",
        "authorization_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/auth",
        "token_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/token",
        "userinfo_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/userinfo",
        "jwks_uri": "https://keycloak.example.com/realms/test/protocol/openid-connect/certs",
        "end_session_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/logout",
    }


@pytest.fixture
def mock_jwks(rsa_keypair):
    """Standard JWKS response."""
    return {"keys": [rsa_keypair["jwk"]]}


def sign_test_id_token(rsa_keypair, claims: dict) -> str:
    """Sign test ID token with ephemeral key."""
    private_key = rsa_keypair["private_key"]
    token = jwt.encode(claims, private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ), algorithm="RS256", headers={"kid": "test-key-1"})
    return token


@pytest.mark.asyncio
async def test_discover_provider_success(mock_provider_metadata):
    """Discover provider metadata."""
    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_provider_metadata
        mock_client.get.return_value = mock_resp

        metadata = await oidc.discover_provider("https://keycloak.example.com/realms/test")

        assert metadata["issuer"] == "https://keycloak.example.com/realms/test"
        assert "authorization_endpoint" in metadata
        assert "token_endpoint" in metadata
        assert "jwks_uri" in metadata


@pytest.mark.asyncio
async def test_discover_provider_missing_endpoints(mock_provider_metadata):
    """Discovery should fail if required endpoints missing."""
    incomplete = {
        "issuer": "https://test.example.com",
        "authorization_endpoint": "https://test.example.com/auth",
        # Missing token_endpoint and jwks_uri
    }

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.json.return_value = incomplete
        mock_client.get.return_value = mock_resp

        with pytest.raises(OIDCError, match="missing required endpoints"):
            await oidc.discover_provider("https://test.example.com")


@pytest.mark.asyncio
async def test_discover_provider_caching(mock_provider_metadata):
    """Discovery should cache results."""
    # Clear cache first
    oidc._discovery_cache.clear()

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_provider_metadata
        mock_client.get.return_value = mock_resp

        # First call
        await oidc.discover_provider("https://keycloak.example.com/realms/test")
        assert mock_client.get.call_count == 1

        # Second call (should use cache)
        await oidc.discover_provider("https://keycloak.example.com/realms/test")
        assert mock_client.get.call_count == 1  # No additional call


@pytest.mark.asyncio
async def test_get_jwks(mock_provider_metadata, mock_jwks):
    """Fetch JWKS from provider."""
    oidc._discovery_cache.clear()
    oidc._jwks_cache.clear()

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        # First GET: discovery
        disc_resp = MagicMock()
        disc_resp.json.return_value = mock_provider_metadata

        # Second GET: JWKS
        jwks_resp = MagicMock()
        jwks_resp.json.return_value = mock_jwks

        mock_client.get.side_effect = [disc_resp, jwks_resp]

        jwks = await oidc.get_jwks("https://keycloak.example.com/realms/test")

        assert "keys" in jwks
        assert len(jwks["keys"]) == 1
        assert jwks["keys"][0]["kid"] == "test-key-1"


def test_build_authorization_url(mock_provider_metadata):
    """Build authorization URL with PKCE."""
    url = oidc.build_authorization_url(
        mock_provider_metadata,
        client_id="test-app",
        redirect_uri="http://localhost:5173/callback",
        state="state123",
        nonce="nonce456",
        code_challenge="challenge789",
        scopes=["openid", "profile", "email"],
    )

    assert "client_id=test-app" in url
    assert "redirect_uri=" in url
    assert "state=state123" in url
    assert "nonce=nonce456" in url
    assert "code_challenge=challenge789" in url
    assert "code_challenge_method=S256" in url


@pytest.mark.asyncio
async def test_exchange_code_success(mock_provider_metadata, rsa_keypair):
    """Exchange authorization code for tokens."""
    id_token = sign_test_id_token(rsa_keypair, {
        "iss": "https://keycloak.example.com/realms/test",
        "sub": "user123",
        "aud": "test-app",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
        "nonce": "nonce456",
        "preferred_username": "testuser",
        "email": "test@example.com",
    })

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "access123",
            "id_token": id_token,
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_client.post.return_value = mock_resp

        tokens = await oidc.exchange_code(
            mock_provider_metadata,
            client_id="test-app",
            client_secret="secret123",
            code="code456",
            code_verifier="verifier789",
            redirect_uri="http://localhost:5173/callback",
        )

        assert tokens["access_token"] == "access123"
        assert tokens["id_token"] == id_token


def test_pkce_generation():
    """PKCE verifier and challenge generation."""
    verifier, challenge = oidc.generate_pkce_pair()

    # Verifier should be URL-safe and ~43 chars
    assert len(verifier) >= 43
    assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in verifier)

    # Challenge should be S256 of verifier
    expected_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    assert challenge == expected_challenge


def test_state_and_nonce_generation():
    """Generate random state and nonce."""
    state, nonce = oidc.generate_state_and_nonce()

    assert len(state) >= 43
    assert len(nonce) >= 43
    assert state != nonce  # Should be different


def test_store_and_validate_state():
    """Store and validate state with provider context."""
    from uuid import uuid4

    oidc._state_store.clear()
    state, nonce = oidc.generate_state_and_nonce()
    verifier, _ = oidc.generate_pkce_pair()
    provider_id = uuid4()

    oidc.store_state(state, provider_id, nonce, verifier)

    retrieved_provider_id, retrieved_nonce, retrieved_verifier = oidc.validate_and_consume_state(state)

    assert str(provider_id) == retrieved_provider_id
    assert nonce == retrieved_nonce
    assert verifier == retrieved_verifier

    # Should fail second time (consumed)
    with pytest.raises(OIDCError, match="Invalid or missing state"):
        oidc.validate_and_consume_state(state)


def test_state_expiry():
    """State should expire after TTL."""
    from uuid import uuid4

    oidc._state_store.clear()
    state, nonce = oidc.generate_state_and_nonce()
    verifier, _ = oidc.generate_pkce_pair()

    # Manually set state to expired
    oidc._state_store[state] = {
        "provider_id": str(uuid4()),
        "nonce": nonce,
        "code_verifier": verifier,
        "expires_at": time.time() - 1,  # Already expired
    }

    with pytest.raises(OIDCError, match="expired"):
        oidc.validate_and_consume_state(state)

    # Should be cleared
    assert state not in oidc._state_store


@pytest.mark.asyncio
async def test_verify_id_token_success(rsa_keypair, mock_provider_metadata, mock_jwks):
    """Verify valid ID token."""
    oidc._discovery_cache.clear()
    oidc._jwks_cache.clear()

    nonce = "test_nonce_123"
    now = int(time.time())
    claims = {
        "iss": "https://keycloak.example.com/realms/test",
        "sub": "user123",
        "aud": "test-app",
        "exp": now + 3600,
        "iat": now,
        "nonce": nonce,
        "preferred_username": "testuser",
        "email": "test@example.com",
    }

    id_token = sign_test_id_token(rsa_keypair, claims)

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        # First GET: discovery
        disc_resp = MagicMock()
        disc_resp.json.return_value = mock_provider_metadata

        # Second GET: JWKS
        jwks_resp = MagicMock()
        jwks_resp.json.return_value = mock_jwks

        mock_client.get.side_effect = [disc_resp, jwks_resp]

        verified = await oidc.verify_id_token(id_token, mock_provider_metadata, "test-app", nonce)

        assert verified["sub"] == "user123"
        assert verified["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_verify_id_token_wrong_issuer(rsa_keypair, mock_provider_metadata, mock_jwks):
    """ID token with wrong issuer should fail."""
    oidc._discovery_cache.clear()
    oidc._jwks_cache.clear()
    nonce = "test_nonce"
    now = int(time.time())
    claims = {
        "iss": "https://wrong-issuer.example.com",  # Wrong issuer
        "sub": "user123",
        "aud": "test-app",
        "exp": now + 3600,
        "iat": now,
        "nonce": nonce,
    }

    id_token = sign_test_id_token(rsa_keypair, claims)

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        disc_resp = MagicMock()
        disc_resp.json.return_value = mock_provider_metadata
        jwks_resp = MagicMock()
        jwks_resp.json.return_value = mock_jwks

        mock_client.get.side_effect = [disc_resp, jwks_resp]

        with pytest.raises(OIDCError, match="Issuer mismatch"):
            await oidc.verify_id_token(id_token, mock_provider_metadata, "test-app", nonce)


@pytest.mark.asyncio
async def test_verify_id_token_expired(rsa_keypair, mock_provider_metadata, mock_jwks):
    """Expired ID token should fail."""
    oidc._discovery_cache.clear()
    oidc._jwks_cache.clear()
    nonce = "test_nonce"
    now = int(time.time())
    claims = {
        "iss": "https://keycloak.example.com/realms/test",
        "sub": "user123",
        "aud": "test-app",
        "exp": now - 100,  # Expired 100 seconds ago
        "iat": now - 3600,
        "nonce": nonce,
    }

    id_token = sign_test_id_token(rsa_keypair, claims)

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        disc_resp = MagicMock()
        disc_resp.json.return_value = mock_provider_metadata
        jwks_resp = MagicMock()
        jwks_resp.json.return_value = mock_jwks

        mock_client.get.side_effect = [disc_resp, jwks_resp]

        with pytest.raises(OIDCError, match="expired"):
            await oidc.verify_id_token(id_token, mock_provider_metadata, "test-app", nonce)


@pytest.mark.asyncio
async def test_verify_id_token_nonce_mismatch(rsa_keypair, mock_provider_metadata, mock_jwks):
    """Nonce mismatch should fail."""
    oidc._discovery_cache.clear()
    oidc._jwks_cache.clear()
    now = int(time.time())
    claims = {
        "iss": "https://keycloak.example.com/realms/test",
        "sub": "user123",
        "aud": "test-app",
        "exp": now + 3600,
        "iat": now,
        "nonce": "token_nonce",
    }

    id_token = sign_test_id_token(rsa_keypair, claims)

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        disc_resp = MagicMock()
        disc_resp.json.return_value = mock_provider_metadata
        jwks_resp = MagicMock()
        jwks_resp.json.return_value = mock_jwks

        mock_client.get.side_effect = [disc_resp, jwks_resp]

        with pytest.raises(OIDCError, match="Nonce mismatch"):
            await oidc.verify_id_token(id_token, mock_provider_metadata, "test-app", "expected_nonce")


@pytest.mark.asyncio
async def test_verify_id_token_wrong_audience(rsa_keypair, mock_provider_metadata, mock_jwks):
    """Wrong audience should fail."""
    oidc._discovery_cache.clear()
    oidc._jwks_cache.clear()
    nonce = "test_nonce"
    now = int(time.time())
    claims = {
        "iss": "https://keycloak.example.com/realms/test",
        "sub": "user123",
        "aud": "other-app",  # Wrong audience
        "exp": now + 3600,
        "iat": now,
        "nonce": nonce,
    }

    id_token = sign_test_id_token(rsa_keypair, claims)

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        disc_resp = MagicMock()
        disc_resp.json.return_value = mock_provider_metadata
        jwks_resp = MagicMock()
        jwks_resp.json.return_value = mock_jwks

        mock_client.get.side_effect = [disc_resp, jwks_resp]

        with pytest.raises(OIDCError, match="Audience mismatch"):
            await oidc.verify_id_token(id_token, mock_provider_metadata, "test-app", nonce)


def test_clear_expired_states():
    """Clear expired states."""
    from uuid import uuid4

    oidc._state_store.clear()

    # Add one valid, one expired
    valid_state = "valid123"
    expired_state = "expired456"

    oidc._state_store[valid_state] = {
        "provider_id": str(uuid4()),
        "nonce": "nonce1",
        "code_verifier": "verifier1",
        "expires_at": time.time() + 3600,
    }

    oidc._state_store[expired_state] = {
        "provider_id": str(uuid4()),
        "nonce": "nonce2",
        "code_verifier": "verifier2",
        "expires_at": time.time() - 1,
    }

    oidc.clear_expired_states()

    assert valid_state in oidc._state_store
    assert expired_state not in oidc._state_store
