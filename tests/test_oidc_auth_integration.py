"""Integration and E2E tests for OIDC login/callback flow."""

import base64
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from backend.app.api import oidc
from backend.app.api.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def admin_token():
    """Admin JWT."""
    from backend.app.api.auth import create_access_token
    return create_access_token({"sub": "admin", "is_admin": True})


@pytest.fixture
def rsa_keypair():
    """Ephemeral RSA keypair for signing test ID tokens."""
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
        "kid": "test-key-1",
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


@pytest.fixture
def setup_oidc_provider(client, admin_token, rsa_keypair):
    """Create and return test OIDC provider."""
    provider_config = {
        "issuer": "https://keycloak.example.com/realms/test",
        "client_id": "test-app",
        "client_secret": "test-secret",
        "redirect_uri": "http://localhost:5173/auth/oidc/callback",
        "scopes": ["openid", "profile", "email"],
        "claim_mappings": {
            "username": "preferred_username",
            "email": "email",
            "is_admin": {"claim": "groups", "match": "finna-admins"},
        },
        "auto_provision": True,
        "allowed_email_domains": ["example.com", "acme.co"],
    }

    response = client.post(
        "/api/v1/auth/providers",
        json={
            "name": "Test Keycloak",
            "kind": "oidc",
            "enabled": True,
            "config": provider_config,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    return response.json()


def sign_test_id_token(rsa_keypair, claims: dict) -> str:
    """Sign test ID token."""
    from cryptography.hazmat.primitives import serialization

    private_key = rsa_keypair["private_key"]
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    token = jwt.encode(claims, pem, algorithm="RS256", headers={"kid": "test-key-1"})
    return token


@pytest.mark.asyncio
async def test_list_enabled_providers(client, setup_oidc_provider):
    """List enabled OIDC providers (public endpoint)."""
    response = client.get("/api/v1/auth/oidc/providers")

    assert response.status_code == 200
    providers = response.json()
    assert len(providers) > 0
    assert providers[0]["name"] == "Test Keycloak"
    assert providers[0]["issuer"] == "https://keycloak.example.com/realms/test"
    assert "enabled" in providers[0]
    # Secrets should not be exposed in public listing
    assert "client_secret" not in str(providers)


@pytest.mark.asyncio
async def test_oidc_login_flow(client, setup_oidc_provider):
    """Test login initiation with PKCE."""
    oidc._discovery_cache.clear()
    oidc._state_store.clear()

    metadata = {
        "issuer": "https://keycloak.example.com/realms/test",
        "authorization_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/auth",
        "token_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/token",
        "jwks_uri": "https://keycloak.example.com/realms/test/protocol/openid-connect/certs",
    }

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        disc_resp = AsyncMock()
        disc_resp.status_code = 200
        disc_resp.json.return_value = metadata
        mock_client.get.return_value = disc_resp

        response = client.post(
            "/api/v1/auth/oidc/login",
            json={"provider_id": setup_oidc_provider["id"]},
        )

    assert response.status_code == 200
    data = response.json()
    assert "authorization_url" in data
    assert "state" in data
    assert "client_id=test-app" in data["authorization_url"]
    assert "code_challenge" in data["authorization_url"]
    assert "code_challenge_method=S256" in data["authorization_url"]
    assert "nonce=" in data["authorization_url"]

    # State should be stored
    assert data["state"] in oidc._state_store


@pytest.mark.asyncio
async def test_oidc_callback_happy_path_new_user(client, setup_oidc_provider, rsa_keypair):
    """Happy path: callback creates new user with auto-provisioning."""
    oidc._discovery_cache.clear()
    oidc._state_store.clear()

    # Step 1: Initiate login (get state)
    metadata = {
        "issuer": "https://keycloak.example.com/realms/test",
        "authorization_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/auth",
        "token_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/token",
        "jwks_uri": "https://keycloak.example.com/realms/test/protocol/openid-connect/certs",
    }

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        disc_resp = AsyncMock()
        disc_resp.json.return_value = metadata
        mock_client.get.return_value = disc_resp

        login_response = client.post(
            "/api/v1/auth/oidc/login",
            json={"provider_id": setup_oidc_provider["id"]},
        )

    assert login_response.status_code == 200
    state = login_response.json()["state"]

    # Step 2: Callback with authorization code
    now = int(time.time())
    id_token_claims = {
        "iss": "https://keycloak.example.com/realms/test",
        "sub": "user_12345",
        "aud": "test-app",
        "exp": now + 3600,
        "iat": now,
        "nonce": oidc._state_store[state]["nonce"],
        "preferred_username": "testuser",
        "email": "testuser@example.com",
        "groups": ["users"],  # Not in finna-admins
    }

    id_token = sign_test_id_token(rsa_keypair, id_token_claims)

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        # Discovery
        disc_resp = AsyncMock()
        disc_resp.json.return_value = metadata
        mock_client.get.side_effect = [disc_resp]

        # Token exchange
        token_resp = AsyncMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {
            "access_token": "access_token_123",
            "id_token": id_token,
            "token_type": "Bearer",
        }
        mock_client.post.return_value = token_resp

        callback_response = client.post(
            "/api/v1/auth/oidc/callback",
            json={
                "provider_id": setup_oidc_provider["id"],
                "code": "authz_code_123",
                "state": state,
            },
        )

    assert callback_response.status_code == 200
    data = callback_response.json()
    assert "token" in data
    assert data["username"] == "testuser"

    # State should be consumed
    assert state not in oidc._state_store

    # Verify JWT
    from backend.app.api.auth import decode_token
    decoded = decode_token(data["token"])
    assert decoded["sub"] == "testuser"
    assert decoded["is_admin"] is False


@pytest.mark.asyncio
async def test_oidc_callback_happy_path_existing_user_is_admin(client, setup_oidc_provider, rsa_keypair):
    """Callback with existing user — update is_admin from group membership."""
    from backend.app.api.db import get_connection

    oidc._discovery_cache.clear()
    oidc._state_store.clear()

    # Pre-create user linked to provider
    provider_id = setup_oidc_provider["id"]
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO auth_users (username, email, hashed_password, oidc_provider_id, oidc_subject, is_admin, is_active) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            ("existinguser", "existing@example.com", "hash", provider_id, "user_existing_id", False, True),
        )
    conn.commit()

    # Step 1: Login
    metadata = {
        "issuer": "https://keycloak.example.com/realms/test",
        "authorization_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/auth",
        "token_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/token",
        "jwks_uri": "https://keycloak.example.com/realms/test/protocol/openid-connect/certs",
    }

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client
        disc_resp = AsyncMock()
        disc_resp.json.return_value = metadata
        mock_client.get.return_value = disc_resp

        login_response = client.post(
            "/api/v1/auth/oidc/login",
            json={"provider_id": provider_id},
        )

    state = login_response.json()["state"]

    # Step 2: Callback with user now in admin group
    now = int(time.time())
    id_token_claims = {
        "iss": "https://keycloak.example.com/realms/test",
        "sub": "user_existing_id",
        "aud": "test-app",
        "exp": now + 3600,
        "iat": now,
        "nonce": oidc._state_store[state]["nonce"],
        "preferred_username": "existinguser",
        "email": "existing@example.com",
        "groups": ["finna-admins"],  # Now in admin group!
    }

    id_token = sign_test_id_token(rsa_keypair, id_token_claims)

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        disc_resp = AsyncMock()
        disc_resp.json.return_value = metadata
        mock_client.get.side_effect = [disc_resp]

        token_resp = AsyncMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {
            "access_token": "access_token_456",
            "id_token": id_token,
        }
        mock_client.post.return_value = token_resp

        callback_response = client.post(
            "/api/v1/auth/oidc/callback",
            json={
                "provider_id": provider_id,
                "code": "authz_code_456",
                "state": state,
            },
        )

    assert callback_response.status_code == 200
    data = callback_response.json()

    # Verify user is now admin
    from backend.app.api.auth import decode_token
    decoded = decode_token(data["token"])
    assert decoded["is_admin"] is True


@pytest.mark.asyncio
async def test_oidc_callback_state_missing(client, setup_oidc_provider):
    """Callback with missing state should fail."""
    response = client.post(
        "/api/v1/auth/oidc/callback",
        json={
            "provider_id": setup_oidc_provider["id"],
            "code": "authz_code",
            "state": "invalid_state",
        },
    )

    assert response.status_code == 400
    assert "state" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_oidc_callback_state_consumed(client, setup_oidc_provider):
    """Using consumed state twice should fail."""
    oidc._state_store.clear()

    metadata = {
        "issuer": "https://keycloak.example.com/realms/test",
        "authorization_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/auth",
        "token_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/token",
        "jwks_uri": "https://keycloak.example.com/realms/test/protocol/openid-connect/certs",
    }

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client
        disc_resp = AsyncMock()
        disc_resp.json.return_value = metadata
        mock_client.get.return_value = disc_resp

        login_response = client.post(
            "/api/v1/auth/oidc/login",
            json={"provider_id": setup_oidc_provider["id"]},
        )

    state = login_response.json()["state"]

    # Manually consume the state
    oidc.validate_and_consume_state(state)

    # Try to use it again
    response = client.post(
        "/api/v1/auth/oidc/callback",
        json={
            "provider_id": setup_oidc_provider["id"],
            "code": "authz_code",
            "state": state,
        },
    )

    assert response.status_code == 400
    assert "state" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_oidc_callback_email_domain_filtering(client, rsa_keypair):
    """Email domain filtering should block disallowed domains."""
    oidc._discovery_cache.clear()
    oidc._state_store.clear()

    # Create provider with email domain restriction
    from backend.app.api.auth import create_access_token
    admin_token = create_access_token({"sub": "admin", "is_admin": True})

    provider_response = client.post(
        "/api/v1/auth/providers",
        json={
            "name": "Restricted Domain",
            "kind": "oidc",
            "enabled": True,
            "config": {
                "issuer": "https://keycloak.example.com/realms/test",
                "client_id": "test-app",
                "client_secret": "secret",
                "redirect_uri": "http://localhost:5173/auth/oidc/callback",
                "claim_mappings": {"username": "preferred_username", "email": "email"},
                "auto_provision": True,
                "allowed_email_domains": ["allowed.com"],  # Only allow allowed.com
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    provider_id = provider_response.json()["id"]

    # Login
    metadata = {
        "issuer": "https://keycloak.example.com/realms/test",
        "authorization_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/auth",
        "token_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/token",
        "jwks_uri": "https://keycloak.example.com/realms/test/protocol/openid-connect/certs",
    }

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client
        disc_resp = AsyncMock()
        disc_resp.json.return_value = metadata
        mock_client.get.return_value = disc_resp

        login_response = client.post(
            "/api/v1/auth/oidc/login",
            json={"provider_id": provider_id},
        )

    state = login_response.json()["state"]

    # Callback with disallowed domain
    now = int(time.time())
    id_token_claims = {
        "iss": "https://keycloak.example.com/realms/test",
        "sub": "user_disallowed",
        "aud": "test-app",
        "exp": now + 3600,
        "iat": now,
        "nonce": oidc._state_store[state]["nonce"],
        "preferred_username": "baduser",
        "email": "baduser@disallowed.com",  # NOT in allowed.com
    }

    id_token = sign_test_id_token(rsa_keypair, id_token_claims)

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client
        disc_resp = AsyncMock()
        disc_resp.json.return_value = metadata
        mock_client.get.side_effect = [disc_resp]
        token_resp = AsyncMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {
            "access_token": "access",
            "id_token": id_token,
        }
        mock_client.post.return_value = token_resp

        callback_response = client.post(
            "/api/v1/auth/oidc/callback",
            json={
                "provider_id": provider_id,
                "code": "code",
                "state": state,
            },
        )

    assert callback_response.status_code == 403
    assert "domain not allowed" in callback_response.json()["detail"]


@pytest.mark.asyncio
async def test_oidc_callback_auto_provision_disabled(client, rsa_keypair):
    """New user without auto-provision should fail."""
    oidc._discovery_cache.clear()
    oidc._state_store.clear()

    # Create provider with auto_provision=false
    from backend.app.api.auth import create_access_token
    admin_token = create_access_token({"sub": "admin", "is_admin": True})

    provider_response = client.post(
        "/api/v1/auth/providers",
        json={
            "name": "No Auto Provision",
            "kind": "oidc",
            "enabled": True,
            "config": {
                "issuer": "https://keycloak.example.com/realms/test",
                "client_id": "test-app",
                "client_secret": "secret",
                "redirect_uri": "http://localhost:5173/auth/oidc/callback",
                "claim_mappings": {"username": "preferred_username", "email": "email"},
                "auto_provision": False,  # DISABLED
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    provider_id = provider_response.json()["id"]

    # Login
    metadata = {
        "issuer": "https://keycloak.example.com/realms/test",
        "authorization_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/auth",
        "token_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/token",
        "jwks_uri": "https://keycloak.example.com/realms/test/protocol/openid-connect/certs",
    }

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client
        disc_resp = AsyncMock()
        disc_resp.json.return_value = metadata
        mock_client.get.return_value = disc_resp

        login_response = client.post(
            "/api/v1/auth/oidc/login",
            json={"provider_id": provider_id},
        )

    state = login_response.json()["state"]

    # Callback with new user
    now = int(time.time())
    id_token_claims = {
        "iss": "https://keycloak.example.com/realms/test",
        "sub": "new_user_456",
        "aud": "test-app",
        "exp": now + 3600,
        "iat": now,
        "nonce": oidc._state_store[state]["nonce"],
        "preferred_username": "newuser",
        "email": "new@example.com",
    }

    id_token = sign_test_id_token(rsa_keypair, id_token_claims)

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client
        disc_resp = AsyncMock()
        disc_resp.json.return_value = metadata
        mock_client.get.side_effect = [disc_resp]
        token_resp = AsyncMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {
            "access_token": "access",
            "id_token": id_token,
        }
        mock_client.post.return_value = token_resp

        callback_response = client.post(
            "/api/v1/auth/oidc/callback",
            json={
                "provider_id": provider_id,
                "code": "code",
                "state": state,
            },
        )

    assert callback_response.status_code == 403
    assert "not provisioned" in callback_response.json()["detail"]


@pytest.mark.asyncio
async def test_oidc_rate_limiting(client, setup_oidc_provider):
    """Rate limiting on login attempts."""
    oidc._discovery_cache.clear()

    metadata = {
        "issuer": "https://keycloak.example.com/realms/test",
        "authorization_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/auth",
        "token_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/token",
        "jwks_uri": "https://keycloak.example.com/realms/test/protocol/openid-connect/certs",
    }

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client
        disc_resp = AsyncMock()
        disc_resp.json.return_value = metadata
        mock_client.get.return_value = disc_resp

        # Make 10 requests (should all succeed)
        for i in range(10):
            response = client.post(
                "/api/v1/auth/oidc/login",
                json={"provider_id": setup_oidc_provider["id"]},
            )
            assert response.status_code == 200

        # 11th should be rate-limited
        response = client.post(
            "/api/v1/auth/oidc/login",
            json={"provider_id": setup_oidc_provider["id"]},
        )
        assert response.status_code == 429
        assert "Too many" in response.json()["detail"]


@pytest.mark.asyncio
async def test_provider_test_endpoint(client, setup_oidc_provider, admin_token):
    """Test provider discovery endpoint."""
    metadata = {
        "issuer": "https://keycloak.example.com/realms/test",
        "authorization_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/auth",
        "token_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/token",
        "jwks_uri": "https://keycloak.example.com/realms/test/protocol/openid-connect/certs",
        "userinfo_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/userinfo",
    }

    jwks = {"keys": [{"kid": "key1", "alg": "RS256"}]}

    with patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        disc_resp = AsyncMock()
        disc_resp.json.return_value = metadata
        jwks_resp = AsyncMock()
        jwks_resp.json.return_value = jwks

        mock_client.get.side_effect = [disc_resp, jwks_resp]

        response = client.post(
            "/api/v1/auth/oidc/test",
            json={"provider_id": setup_oidc_provider["id"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["provider_name"] == "Test Keycloak"
    assert data["issuer"] == "https://keycloak.example.com/realms/test"
    assert "endpoints" in data
    assert data["jwks_keys_count"] == 1
