"""Integration tests for OIDC device authorization flow (RFC 8628).

All DB calls are mocked — no Postgres required.
"""

from __future__ import annotations

import base64
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from backend.app.api import oidc
from backend.app.api.main import app
from utils.encryption import encrypt_config


@pytest.fixture
def client():
    """FastAPI test client."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def rsa_keypair():
    """Ephemeral RSA keypair for signing test ID tokens."""
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

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
        "jwk": jwk,
    }


def _make_provider_config():
    """Build OIDC provider config dict."""
    return {
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


def _make_provider_row(config=None):
    """Build a mock DB row for an OIDC provider."""
    cfg = config or _make_provider_config()
    return {
        "id": str(uuid.uuid4()),
        "config": encrypt_config(cfg),
    }


def _mock_query_one_factory(provider_row):
    """Return a mock query_one that returns provider for provider queries, None for user queries."""
    def mock_query_one(sql, params=None):
        if "auth_providers" in sql:
            return provider_row
        return None
    return mock_query_one


async def _mock_get_jwks(issuer):
    """Return JWKS containing the test RSA key."""
    return {"keys": [rsa_keypair_for_mock["jwk"]]}


rsa_keypair_for_mock: dict = {}


def _mock_get_jwks_factory(keypair):
    """Return a mock get_jwks that returns the test RSA key."""
    async def mock_get_jwks(issuer):
        return {"keys": [keypair["jwk"]]}
    return mock_get_jwks


def sign_test_id_token(rsa_keypair, claims: dict) -> str:
    """Sign test ID token."""
    from cryptography.hazmat.primitives import serialization

    private_key = rsa_keypair["private_key"]
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": "test-key-1"})


DEVICE_AUTH_METADATA = {
    "issuer": "https://keycloak.example.com/realms/test",
    "authorization_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/auth",
    "token_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/token",
    "jwks_uri": "https://keycloak.example.com/realms/test/protocol/openid-connect/certs",
    "device_authorization_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/device",
}


def test_device_start_returns_required_fields(client, rsa_keypair):
    """Device start returns device_code, user_code, verification_uri."""
    oidc._discovery_cache.clear()
    oidc._device_code_store.clear()

    provider_row = _make_provider_row()

    device_auth_response = {
        "device_code": "GmRhmhcxhwAzkoEqiMEg_DnyEysNkuNh",
        "user_code": "WDJB-MJHT",
        "verification_uri": "https://keycloak.example.com/device",
        "verification_uri_complete": "https://keycloak.example.com/device?user_code=WDJB-MJHT",
        "expires_in": 600,
        "interval": 5,
    }

    with patch("backend.app.api.routes.oidc_device_auth.query_one", return_value=provider_row), \
         patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:

        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        disc_resp = MagicMock()
        disc_resp.status_code = 200
        disc_resp.json.return_value = DEVICE_AUTH_METADATA
        mock_client.get.return_value = disc_resp

        dev_resp = MagicMock()
        dev_resp.status_code = 200
        dev_resp.json.return_value = device_auth_response
        mock_client.post.return_value = dev_resp

        response = client.post(
            "/api/v1/auth/oidc/device",
            json={"provider_id": provider_row["id"]},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["device_code"] == "GmRhmhcxhwAzkoEqiMEg_DnyEysNkuNh"
    assert data["user_code"] == "WDJB-MJHT"
    assert data["verification_uri"] == "https://keycloak.example.com/device"
    assert data["verification_uri_complete"] == "https://keycloak.example.com/device?user_code=WDJB-MJHT"
    assert data["expires_in"] == 600
    assert data["interval"] == 5

    assert "GmRhmhcxhwAzkoEqiMEg_DnyEysNkuNh" in oidc._device_code_store


def test_device_start_provider_not_found(client):
    """Device start with non-existent provider returns 404."""
    with patch("backend.app.api.routes.oidc_device_auth.query_one", return_value=None):
        response = client.post(
            "/api/v1/auth/oidc/device",
            json={"provider_id": str(uuid.uuid4())},
        )
    assert response.status_code == 404


def test_device_start_no_device_endpoint(client):
    """Device start returns 400 when provider lacks device_authorization_endpoint."""
    oidc._discovery_cache.clear()
    provider_row = _make_provider_row()

    metadata_without_device = {
        "issuer": "https://keycloak.example.com/realms/test",
        "authorization_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/auth",
        "token_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/token",
        "jwks_uri": "https://keycloak.example.com/realms/test/protocol/openid-connect/certs",
    }

    with patch("backend.app.api.routes.oidc_device_auth.query_one", return_value=provider_row), \
         patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:

        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        disc_resp = MagicMock()
        disc_resp.status_code = 200
        disc_resp.json.return_value = metadata_without_device
        mock_client.get.return_value = disc_resp

        response = client.post(
            "/api/v1/auth/oidc/device",
            json={"provider_id": provider_row["id"]},
        )

    assert response.status_code == 400
    assert "device authorization" in response.json()["detail"].lower()


def test_device_poll_pending(client):
    """Poll returns pending when user hasn't completed auth."""
    oidc._discovery_cache.clear()
    oidc._device_code_store.clear()

    device_code = "test-pending-device-code"
    provider_row = _make_provider_row()

    oidc.store_device_code(
        device_code=device_code,
        provider_id=provider_row["id"],
        client_id="test-app",
        client_secret="test-secret",
        interval=5,
        expires_in=600,
    )

    with patch("backend.app.api.routes.oidc_device_auth.query_one", return_value=provider_row), \
         patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:

        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        disc_resp = MagicMock()
        disc_resp.json.return_value = DEVICE_AUTH_METADATA
        mock_client.get.return_value = disc_resp

        pending_resp = MagicMock()
        pending_resp.status_code = 400
        pending_resp.json.return_value = {
            "error": "authorization_pending",
            "error_description": "The authorization request is still pending",
        }
        mock_client.post.return_value = pending_resp

        response = client.post(
            "/api/v1/auth/oidc/device/callback",
            json={"device_code": device_code},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["token"] is None

    assert device_code in oidc._device_code_store


def test_device_poll_completed(client, rsa_keypair):
    """Poll returns JWT when user completes auth."""
    oidc._discovery_cache.clear()
    oidc._device_code_store.clear()
    oidc._jwks_cache.clear()

    device_code = "test-completed-device-code"
    provider_row = _make_provider_row()

    oidc.store_device_code(
        device_code=device_code,
        provider_id=provider_row["id"],
        client_id="test-app",
        client_secret="test-secret",
        interval=5,
        expires_in=600,
    )

    now = int(time.time())
    id_token_claims = {
        "iss": "https://keycloak.example.com/realms/test",
        "sub": "device_user_12345",
        "aud": "test-app",
        "exp": now + 3600,
        "iat": now,
        "preferred_username": "deviceuser",
        "email": "deviceuser@example.com",
        "groups": ["users"],
    }
    id_token = sign_test_id_token(rsa_keypair, id_token_claims)

    def mock_insert_and_return(sql, params=None):
        return 42

    def mock_execute(sql, params=None):
        pass

    with patch("backend.app.api.routes.oidc_device_auth.query_one",
               side_effect=_mock_query_one_factory(provider_row)), \
         patch("backend.app.api.routes.oidc_device_auth.insert_and_return",
               side_effect=mock_insert_and_return), \
         patch("backend.app.api.routes.oidc_device_auth.execute",
               side_effect=mock_execute), \
         patch("backend.app.api.oidc.get_jwks",
               side_effect=_mock_get_jwks_factory(rsa_keypair)), \
         patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:

        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        disc_resp = MagicMock()
        disc_resp.json.return_value = DEVICE_AUTH_METADATA
        mock_client.get.return_value = disc_resp

        token_resp = MagicMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {
            "access_token": "access_token_123",
            "id_token": id_token,
            "token_type": "Bearer",
        }
        mock_client.post.return_value = token_resp

        response = client.post(
            "/api/v1/auth/oidc/device/callback",
            json={"device_code": device_code},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "token" in data
    assert data["username"] == "deviceuser"
    assert data["user_id"] == 42

    assert device_code not in oidc._device_code_store

    from backend.app.api.auth import decode_token
    decoded = decode_token(data["token"])
    assert decoded["sub"] == "deviceuser"
    assert decoded["is_admin"] is False


def test_device_poll_expired(client):
    """Poll returns 404 when device code has expired."""
    oidc._device_code_store.clear()

    device_code = "test-expired-device-code"
    provider_row = _make_provider_row()

    oidc._device_code_store[device_code] = {
        "provider_id": provider_row["id"],
        "client_id": "test-app",
        "client_secret": "test-secret",
        "interval": 5,
        "expires_at": time.time() - 10,
    }

    response = client.post(
        "/api/v1/auth/oidc/device/callback",
        json={"device_code": device_code},
    )

    assert response.status_code == 404


def test_device_poll_invalid_code(client):
    """Poll returns 404 for unknown device code."""
    response = client.post(
        "/api/v1/auth/oidc/device/callback",
        json={"device_code": "completely-unknown-code"},
    )
    assert response.status_code == 404


def test_device_poll_access_denied(client):
    """Poll returns denied when user denies authorization."""
    oidc._discovery_cache.clear()
    oidc._device_code_store.clear()

    device_code = "test-denied-device-code"
    provider_row = _make_provider_row()

    oidc.store_device_code(
        device_code=device_code,
        provider_id=provider_row["id"],
        client_id="test-app",
        client_secret="test-secret",
        interval=5,
        expires_in=600,
    )

    with patch("backend.app.api.routes.oidc_device_auth.query_one", return_value=provider_row), \
         patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:

        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        disc_resp = MagicMock()
        disc_resp.json.return_value = DEVICE_AUTH_METADATA
        mock_client.get.return_value = disc_resp

        denied_resp = MagicMock()
        denied_resp.status_code = 400
        denied_resp.json.return_value = {
            "error": "access_denied",
            "error_description": "The user denied the authorization",
        }
        mock_client.post.return_value = denied_resp

        response = client.post(
            "/api/v1/auth/oidc/device/callback",
            json={"device_code": device_code},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "denied"


def test_device_poll_email_domain_filter(client, rsa_keypair):
    """Poll rejects user with non-allowed email domain."""
    oidc._discovery_cache.clear()
    oidc._device_code_store.clear()
    oidc._jwks_cache.clear()

    device_code = "test-domain-filter-device-code"
    provider_row = _make_provider_row()

    oidc.store_device_code(
        device_code=device_code,
        provider_id=provider_row["id"],
        client_id="test-app",
        client_secret="test-secret",
        interval=5,
        expires_in=600,
    )

    now = int(time.time())
    id_token_claims = {
        "iss": "https://keycloak.example.com/realms/test",
        "sub": "user_bad_domain",
        "aud": "test-app",
        "exp": now + 3600,
        "iat": now,
        "preferred_username": "baduser",
        "email": "baduser@unauthorized.com",
        "groups": ["users"],
    }
    id_token = sign_test_id_token(rsa_keypair, id_token_claims)

    with patch("backend.app.api.routes.oidc_device_auth.query_one",
               side_effect=_mock_query_one_factory(provider_row)), \
         patch("backend.app.api.oidc.get_jwks",
               side_effect=_mock_get_jwks_factory(rsa_keypair)), \
         patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:

        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        disc_resp = MagicMock()
        disc_resp.json.return_value = DEVICE_AUTH_METADATA
        mock_client.get.return_value = disc_resp

        token_resp = MagicMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {
            "access_token": "access_token_456",
            "id_token": id_token,
            "token_type": "Bearer",
        }
        mock_client.post.return_value = token_resp

        response = client.post(
            "/api/v1/auth/oidc/device/callback",
            json={"device_code": device_code},
        )

    assert response.status_code == 403
    assert "domain" in response.json()["detail"].lower()


def test_device_poll_missing_claims(client, rsa_keypair):
    """Poll rejects when required claims are missing from ID token."""
    oidc._discovery_cache.clear()
    oidc._device_code_store.clear()
    oidc._jwks_cache.clear()

    device_code = "test-missing-claims-device-code"
    provider_row = _make_provider_row()

    oidc.store_device_code(
        device_code=device_code,
        provider_id=provider_row["id"],
        client_id="test-app",
        client_secret="test-secret",
        interval=5,
        expires_in=600,
    )

    now = int(time.time())
    id_token_claims = {
        "iss": "https://keycloak.example.com/realms/test",
        "sub": "user_no_email",
        "aud": "test-app",
        "exp": now + 3600,
        "iat": now,
        "preferred_username": "noemailuser",
    }
    id_token = sign_test_id_token(rsa_keypair, id_token_claims)

    with patch("backend.app.api.routes.oidc_device_auth.query_one",
               side_effect=_mock_query_one_factory(provider_row)), \
         patch("backend.app.api.oidc.get_jwks",
               side_effect=_mock_get_jwks_factory(rsa_keypair)), \
         patch("backend.app.api.oidc.httpx.AsyncClient") as mock_client_ctx:

        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        disc_resp = MagicMock()
        disc_resp.json.return_value = DEVICE_AUTH_METADATA
        mock_client.get.return_value = disc_resp

        token_resp = MagicMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {
            "access_token": "access_token_789",
            "id_token": id_token,
            "token_type": "Bearer",
        }
        mock_client.post.return_value = token_resp

        response = client.post(
            "/api/v1/auth/oidc/device/callback",
            json={"device_code": device_code},
        )

    assert response.status_code == 400
    assert "claims" in response.json()["detail"].lower()
