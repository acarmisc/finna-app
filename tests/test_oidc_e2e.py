"""End-to-end OIDC flow tests with simulated OAuth2 server."""

import base64
import hashlib
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.api import oidc
from backend.app.api.auth import create_access_token, decode_token
from backend.app.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_token():
    return create_access_token({"sub": "admin", "is_admin": True})


@pytest.fixture
def rsa_keypair():
    """Generate RSA keypair for ID token signing."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    e = public_key.public_numbers().e
    n = public_key.public_numbers().n

    jwk = {
        "kty": "RSA",
        "kid": "e2e-test-key",
        "use": "sig",
        "alg": "RS256",
        "n": base64.urlsafe_b64encode(n.to_bytes(256, "big")).decode().rstrip("="),
        "e": base64.urlsafe_b64encode(e.to_bytes(3, "big")).decode().rstrip("="),
    }

    return {
        "private_key": private_key,
        "private_pem": private_pem,
        "jwk": jwk,
    }


def sign_id_token(rsa_keypair, claims: dict) -> str:
    """Sign ID token with test key."""
    from jose import jwt

    pem = rsa_keypair["private_pem"]
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": "e2e-test-key"})


class MockOAuth2Server:
    """Simulates an OAuth2 provider for E2E testing."""

    def __init__(self, rsa_keypair):
        self.rsa_keypair = rsa_keypair
        self.issuer = "https://e2e-oauth.example.com"
        self.client_id = "test-client"
        self.client_secret = "test-secret"
        self.redirect_uri = "http://localhost:5173/auth/oidc/callback"
        self.authorization_codes: dict[str, dict] = {}
        self.user_db: dict[str, dict] = {
            "user_1": {
                "sub": "user_1",
                "preferred_username": "alice",
                "email": "alice@example.com",
                "groups": ["users"],
            },
            "user_admin": {
                "sub": "user_admin",
                "preferred_username": "bob",
                "email": "bob@example.com",
                "groups": ["users", "finna-admins"],
            },
        }

    async def handle_discovery(self) -> dict:
        """Serve OpenID Configuration."""
        return {
            "issuer": self.issuer,
            "authorization_endpoint": f"{self.issuer}/oauth/authorize",
            "token_endpoint": f"{self.issuer}/oauth/token",
            "userinfo_endpoint": f"{self.issuer}/oauth/userinfo",
            "jwks_uri": f"{self.issuer}/.well-known/jwks.json",
            "end_session_endpoint": f"{self.issuer}/oauth/logout",
            "scopes_supported": ["openid", "profile", "email"],
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
        }

    async def handle_jwks(self) -> dict:
        """Serve JWKS endpoint."""
        return {"keys": [self.rsa_keypair["jwk"]]}

    async def handle_token_request(self, code: str, code_verifier: str) -> dict:
        """Simulate token endpoint."""
        if code not in self.authorization_codes:
            raise ValueError("Invalid authorization code")

        stored = self.authorization_codes[code]

        # Verify code_verifier (PKCE)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")

        if challenge != stored["code_challenge"]:
            raise ValueError("Invalid code_verifier")

        # Get user data
        user_id = stored["user_id"]
        user = self.user_db.get(user_id)
        if not user:
            raise ValueError("User not found")

        # Issue ID token
        now = int(time.time())
        id_token_claims = {
            "iss": self.issuer,
            "sub": user["sub"],
            "aud": self.client_id,
            "exp": now + 3600,
            "iat": now,
            "nonce": stored["nonce"],
            "preferred_username": user["preferred_username"],
            "email": user["email"],
            "groups": user["groups"],
        }

        id_token = sign_id_token(self.rsa_keypair, id_token_claims)

        return {
            "access_token": f"access_{code}",
            "id_token": id_token,
            "token_type": "Bearer",
            "expires_in": 3600,
        }

    def store_authorization_code(self, code: str, user_id: str, nonce: str, code_challenge: str):
        """Store authorization code for token exchange."""
        self.authorization_codes[code] = {
            "user_id": user_id,
            "nonce": nonce,
            "code_challenge": code_challenge,
        }


@pytest.fixture
def oauth2_server(rsa_keypair):
    return MockOAuth2Server(rsa_keypair)


@pytest.mark.asyncio
async def test_e2e_full_login_flow_new_user(client, admin_token, oauth2_server):
    """End-to-end: complete login flow for new user."""
    oidc._discovery_cache.clear()
    oidc._state_store.clear()

    # Step 1: Create OIDC provider
    provider_response = client.post(
        "/api/v1/auth/providers",
        json={
            "name": "E2E OAuth Server",
            "kind": "oidc",
            "enabled": True,
            "config": {
                "issuer": oauth2_server.issuer,
                "client_id": oauth2_server.client_id,
                "client_secret": oauth2_server.client_secret,
                "redirect_uri": oauth2_server.redirect_uri,
                "scopes": ["openid", "profile", "email"],
                "claim_mappings": {
                    "username": "preferred_username",
                    "email": "email",
                    "is_admin": {"claim": "groups", "match": "finna-admins"},
                },
                "auto_provision": True,
                "allowed_email_domains": ["example.com"],
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert provider_response.status_code == 200
    provider_id = provider_response.json()["id"]

    # Step 2: Client requests login URL
    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        # Mock discovery
        disc_resp = AsyncMock()
        disc_resp.json.return_value = await oauth2_server.handle_discovery()
        mock_client.get.return_value = disc_resp

        login_response = client.post(
            "/api/v1/auth/oidc/login",
            json={"provider_id": provider_id},
        )

    assert login_response.status_code == 200
    login_data = login_response.json()
    state = login_data["state"]
    auth_url = login_data["authorization_url"]

    # Verify auth URL structure
    assert "authorization_endpoint" in str(auth_url)
    assert f"client_id={oauth2_server.client_id}" in auth_url
    assert f"state={state}" in auth_url
    assert "code_challenge=" in auth_url
    assert "nonce=" in auth_url

    # Step 3: Simulate user authentication at OAuth2 server and redirect back
    # Extract code_challenge from state store
    stored_state = oidc._state_store[state]
    code_verifier = stored_state["code_verifier"]
    nonce = stored_state["nonce"]
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip("=")

    # OAuth2 server generates authorization code
    auth_code = "e2e_authz_code_user_1"
    oauth2_server.store_authorization_code(auth_code, "user_1", nonce, code_challenge)

    # Step 4: Client exchanges code at callback
    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        # Mock discovery
        disc_resp = AsyncMock()
        disc_resp.json.return_value = await oauth2_server.handle_discovery()

        # Mock token request
        token_resp = AsyncMock()
        token_resp.status_code = 200
        token_resp.json.return_value = await oauth2_server.handle_token_request(auth_code, code_verifier)

        mock_client.get.side_effect = [disc_resp]
        mock_client.post.return_value = token_resp

        callback_response = client.post(
            "/api/v1/auth/oidc/callback",
            json={
                "provider_id": provider_id,
                "code": auth_code,
                "state": state,
            },
        )

    assert callback_response.status_code == 200
    callback_data = callback_response.json()

    # Verify JWT
    assert "token" in callback_data
    assert callback_data["username"] == "alice"

    decoded = decode_token(callback_data["token"])
    assert decoded["sub"] == "alice"
    assert decoded["is_admin"] is False  # User not in finna-admins


@pytest.mark.asyncio
async def test_e2e_user_with_admin_role(client, admin_token, oauth2_server):
    """End-to-end: user with admin group membership."""
    oidc._discovery_cache.clear()
    oidc._state_store.clear()

    # Create provider
    provider_response = client.post(
        "/api/v1/auth/providers",
        json={
            "name": "E2E Admin Test",
            "kind": "oidc",
            "enabled": True,
            "config": {
                "issuer": oauth2_server.issuer,
                "client_id": oauth2_server.client_id,
                "client_secret": oauth2_server.client_secret,
                "redirect_uri": oauth2_server.redirect_uri,
                "claim_mappings": {
                    "username": "preferred_username",
                    "email": "email",
                    "is_admin": {"claim": "groups", "match": "finna-admins"},
                },
                "auto_provision": True,
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    provider_id = provider_response.json()["id"]

    # Login
    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client
        disc_resp = AsyncMock()
        disc_resp.json.return_value = await oauth2_server.handle_discovery()
        mock_client.get.return_value = disc_resp

        login_response = client.post(
            "/api/v1/auth/oidc/login",
            json={"provider_id": provider_id},
        )

    state = login_response.json()["state"]
    stored_state = oidc._state_store[state]
    code_verifier = stored_state["code_verifier"]
    nonce = stored_state["nonce"]

    # Admin user callback
    auth_code = "e2e_authz_code_admin"
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip("=")
    oauth2_server.store_authorization_code(auth_code, "user_admin", nonce, code_challenge)

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client
        disc_resp = AsyncMock()
        disc_resp.json.return_value = await oauth2_server.handle_discovery()
        token_resp = AsyncMock()
        token_resp.status_code = 200
        token_resp.json.return_value = await oauth2_server.handle_token_request(auth_code, code_verifier)
        mock_client.get.side_effect = [disc_resp]
        mock_client.post.return_value = token_resp

        callback_response = client.post(
            "/api/v1/auth/oidc/callback",
            json={
                "provider_id": provider_id,
                "code": auth_code,
                "state": state,
            },
        )

    assert callback_response.status_code == 200
    decoded = decode_token(callback_response.json()["token"])
    assert decoded["is_admin"] is True


@pytest.mark.asyncio
async def test_e2e_invalid_client_secret(client, admin_token, oauth2_server):
    """E2E: token request with wrong secret should fail."""
    oidc._discovery_cache.clear()
    oidc._state_store.clear()

    provider_response = client.post(
        "/api/v1/auth/providers",
        json={
            "name": "Wrong Secret Test",
            "kind": "oidc",
            "enabled": True,
            "config": {
                "issuer": oauth2_server.issuer,
                "client_id": oauth2_server.client_id,
                "client_secret": "WRONG_SECRET",  # Wrong!
                "redirect_uri": oauth2_server.redirect_uri,
                "claim_mappings": {"username": "preferred_username", "email": "email"},
                "auto_provision": True,
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    provider_id = provider_response.json()["id"]

    # Login
    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client
        disc_resp = AsyncMock()
        disc_resp.json.return_value = await oauth2_server.handle_discovery()
        mock_client.get.return_value = disc_resp

        login_response = client.post(
            "/api/v1/auth/oidc/login",
            json={"provider_id": provider_id},
        )

    state = login_response.json()["state"]
    stored_state = oidc._state_store[state]

    # Token exchange with wrong secret
    auth_code = "bad_secret_code"
    oauth2_server.store_authorization_code(auth_code, "user_1", stored_state["nonce"], "dummy")

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        # Simulate OAuth2 server rejecting bad secret
        error_resp = AsyncMock()
        error_resp.status_code = 401
        error_resp.text = "Invalid client secret"
        error_resp.raise_for_status.side_effect = Exception("401 Unauthorized")

        disc_resp = AsyncMock()
        disc_resp.json.return_value = await oauth2_server.handle_discovery()

        mock_client.get.side_effect = [disc_resp]
        mock_client.post.return_value = error_resp

        callback_response = client.post(
            "/api/v1/auth/oidc/callback",
            json={
                "provider_id": provider_id,
                "code": auth_code,
                "state": state,
            },
        )

    # Should fail
    assert callback_response.status_code in [400, 500]


@pytest.mark.asyncio
async def test_e2e_pkce_defense(client, admin_token, oauth2_server):
    """E2E: PKCE defense against authorization code injection."""
    oidc._discovery_cache.clear()
    oidc._state_store.clear()

    provider_response = client.post(
        "/api/v1/auth/providers",
        json={
            "name": "PKCE Test",
            "kind": "oidc",
            "enabled": True,
            "config": {
                "issuer": oauth2_server.issuer,
                "client_id": oauth2_server.client_id,
                "client_secret": oauth2_server.client_secret,
                "redirect_uri": oauth2_server.redirect_uri,
                "claim_mappings": {"username": "preferred_username", "email": "email"},
                "auto_provision": True,
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    provider_id = provider_response.json()["id"]

    # Login
    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client
        disc_resp = AsyncMock()
        disc_resp.json.return_value = await oauth2_server.handle_discovery()
        mock_client.get.return_value = disc_resp

        login_response = client.post(
            "/api/v1/auth/oidc/login",
            json={"provider_id": provider_id},
        )

    state = login_response.json()["state"]
    stored_state = oidc._state_store[state]
    nonce = stored_state["nonce"]

    # Attacker uses code_verifier, not the one generated
    auth_code = "injected_code"
    attacker_verifier = "attacker_verifier_string"
    attacker_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(attacker_verifier.encode()).digest()
    ).decode().rstrip("=")

    # Store with attacker's challenge (not matching the one in state)
    oauth2_server.store_authorization_code(auth_code, "user_1", nonce, attacker_challenge)

    # Callback with attacker's code_verifier (doesn't match stored challenge)
    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client
        disc_resp = AsyncMock()
        disc_resp.json.return_value = await oauth2_server.handle_discovery()
        mock_client.get.side_effect = [disc_resp]

        # Token request with mismatched verifier
        token_resp = AsyncMock()
        token_resp.status_code = 400
        token_resp.text = "Invalid code_verifier"

        def raise_error(*args, **kwargs):
            raise Exception("PKCE verification failed")

        token_resp.json.side_effect = raise_error
        mock_client.post.return_value = token_resp

        callback_response = client.post(
            "/api/v1/auth/oidc/callback",
            json={
                "provider_id": provider_id,
                "code": auth_code,
                "state": state,
            },
        )

    # Should fail due to PKCE mismatch
    assert callback_response.status_code >= 400


@pytest.mark.asyncio
async def test_e2e_multiple_login_sessions(client, admin_token, oauth2_server):
    """E2E: concurrent login sessions remain isolated (state management)."""
    oidc._discovery_cache.clear()
    oidc._state_store.clear()

    provider_response = client.post(
        "/api/v1/auth/providers",
        json={
            "name": "Concurrent Test",
            "kind": "oidc",
            "enabled": True,
            "config": {
                "issuer": oauth2_server.issuer,
                "client_id": oauth2_server.client_id,
                "client_secret": oauth2_server.client_secret,
                "redirect_uri": oauth2_server.redirect_uri,
                "claim_mappings": {"username": "preferred_username", "email": "email"},
                "auto_provision": True,
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    provider_id = provider_response.json()["id"]

    # Start two login sessions
    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client
        disc_resp = AsyncMock()
        disc_resp.json.return_value = await oauth2_server.handle_discovery()
        mock_client.get.return_value = disc_resp

        login1 = client.post("/api/v1/auth/oidc/login", json={"provider_id": provider_id})
        login2 = client.post("/api/v1/auth/oidc/login", json={"provider_id": provider_id})

    state1 = login1.json()["state"]
    state2 = login2.json()["state"]

    # States should be different
    assert state1 != state2

    # Nonces should be different
    assert oidc._state_store[state1]["nonce"] != oidc._state_store[state2]["nonce"]

    # Nonce from session 1 should NOT work with session 2's code
    stored1 = oidc._state_store[state1]
    stored2 = oidc._state_store[state2]

    code_verifier1 = stored1["code_verifier"]
    nonce1 = stored1["nonce"]
    code_challenge1 = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier1.encode()).digest()
    ).decode().rstrip("=")

    auth_code = "multi_session_code"
    oauth2_server.store_authorization_code(auth_code, "user_1", nonce1, code_challenge1)

    # Try to use code from session 1 with state from session 2 (should fail)
    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client
        disc_resp = AsyncMock()
        disc_resp.json.return_value = await oauth2_server.handle_discovery()
        token_resp = AsyncMock()
        token_resp.status_code = 200
        token_resp.json.return_value = await oauth2_server.handle_token_request(auth_code, code_verifier1)
        mock_client.get.side_effect = [disc_resp]
        mock_client.post.return_value = token_resp

        # Wrong state for this code
        callback_response = client.post(
            "/api/v1/auth/oidc/callback",
            json={
                "provider_id": provider_id,
                "code": auth_code,
                "state": state2,  # Different state!
            },
        )

    # Should fail due to state/nonce mismatch
    assert callback_response.status_code == 400
