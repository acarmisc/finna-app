"""Tests for OIDC auth providers CRUD."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.api.main import app


@pytest.fixture
def admin_token():
    """Generate admin JWT for testing."""
    from backend.app.api.auth import create_access_token
    return create_access_token({"sub": "admin", "is_admin": True})


@pytest.fixture
def user_token():
    """Generate regular user JWT for testing."""
    from backend.app.api.auth import create_access_token
    return create_access_token({"sub": "user", "is_admin": False})


@pytest.fixture
def client():
    """FastAPI test client."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_list_providers_requires_admin(client, user_token):
    """List providers should require admin role."""
    response = client.get(
        "/api/v1/auth/providers",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403
    assert "Admin role required" in response.json()["detail"]


def test_create_provider_requires_admin(client, user_token):
    """Create provider should require admin role."""
    response = client.post(
        "/api/v1/auth/providers",
        json={
            "name": "Test",
            "kind": "oidc",
            "config": {
                "issuer": "https://example.com",
                "client_id": "test",
                "client_secret": "secret",
                "redirect_uri": "http://localhost:5173/auth/oidc/callback",
            }
        },
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403


def test_create_provider_success(client, admin_token):
    """Create provider with valid config."""
    response = client.post(
        "/api/v1/auth/providers",
        json={
            "name": "Keycloak Prod",
            "kind": "oidc",
            "enabled": False,
            "config": {
                "issuer": "https://keycloak.example.com/realms/finna",
                "client_id": "finna-app",
                "client_secret": "secret123",
                "redirect_uri": "http://localhost:5173/auth/oidc/callback",
                "scopes": ["openid", "profile", "email"],
                "claim_mappings": {"username": "preferred_username", "email": "email"},
                "auto_provision": False,
                "allowed_email_domains": ["example.com"]
            }
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Keycloak Prod"
    assert data["kind"] == "oidc"
    assert data["enabled"] is False
    # Secrets should be masked
    assert "client_secret" not in data["config"]
    assert data["config"]["issuer"] == "https://keycloak.example.com/realms/finna"
    assert data["config"]["client_id"] == "finna-app"
    assert data["config"]["auto_provision"] is False


def test_create_provider_duplicate_name(client, admin_token):
    """Creating provider with duplicate name should fail."""
    # Create first
    client.post(
        "/api/v1/auth/providers",
        json={
            "name": "Keycloak",
            "kind": "oidc",
            "config": {
                "issuer": "https://kc1.example.com",
                "client_id": "app1",
                "client_secret": "secret1",
                "redirect_uri": "http://localhost:5173/auth/oidc/callback",
            }
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Try to create duplicate
    response = client.post(
        "/api/v1/auth/providers",
        json={
            "name": "Keycloak",
            "kind": "oidc",
            "config": {
                "issuer": "https://kc2.example.com",
                "client_id": "app2",
                "client_secret": "secret2",
                "redirect_uri": "http://localhost:5173/auth/oidc/callback",
            }
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_get_provider_success(client, admin_token):
    """Get single provider."""
    create_resp = client.post(
        "/api/v1/auth/providers",
        json={
            "name": "Get Test",
            "kind": "oidc",
            "config": {
                "issuer": "https://test.example.com",
                "client_id": "test-id",
                "client_secret": "test-secret",
                "redirect_uri": "http://localhost:5173/auth/oidc/callback",
            }
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    provider_id = create_resp.json()["id"]

    response = client.get(
        f"/api/v1/auth/providers/{provider_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == provider_id
    assert response.json()["name"] == "Get Test"
    # Secrets masked
    assert "client_secret" not in response.json()["config"]


def test_update_provider_success(client, admin_token):
    """Update provider."""
    create_resp = client.post(
        "/api/v1/auth/providers",
        json={
            "name": "Original Name",
            "kind": "oidc",
            "enabled": False,
            "config": {
                "issuer": "https://test.example.com",
                "client_id": "test-id",
                "client_secret": "test-secret",
                "redirect_uri": "http://localhost:5173/auth/oidc/callback",
            }
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    provider_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/auth/providers/{provider_id}",
        json={
            "name": "Updated Name",
            "kind": "oidc",
            "enabled": True,
            "config": {
                "issuer": "https://test.example.com",
                "client_id": "new-client-id",
                "client_secret": "new-secret",
                "redirect_uri": "http://localhost:5173/auth/oidc/callback",
                "scopes": ["openid", "profile"],
            }
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"
    assert response.json()["enabled"] is True
    assert response.json()["config"]["client_id"] == "new-client-id"


def test_delete_provider_success(client, admin_token):
    """Delete provider."""
    create_resp = client.post(
        "/api/v1/auth/providers",
        json={
            "name": "Delete Me",
            "kind": "oidc",
            "config": {
                "issuer": "https://test.example.com",
                "client_id": "test",
                "client_secret": "secret",
                "redirect_uri": "http://localhost:5173/auth/oidc/callback",
            }
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    provider_id = create_resp.json()["id"]

    response = client.delete(
        f"/api/v1/auth/providers/{provider_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

    # Verify deleted
    get_resp = client.get(
        f"/api/v1/auth/providers/{provider_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_resp.status_code == 404


def test_delete_provider_with_linked_users(client, admin_token):
    """Delete should fail if users are linked."""
    create_resp = client.post(
        "/api/v1/auth/providers",
        json={
            "name": "Linked Provider",
            "kind": "oidc",
            "config": {
                "issuer": "https://test.example.com",
                "client_id": "test",
                "client_secret": "secret",
                "redirect_uri": "http://localhost:5173/auth/oidc/callback",
            }
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    provider_id = create_resp.json()["id"]

    # Manually insert a user linked to this provider
    from backend.app.api.db import get_connection
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO auth_users (username, email, hashed_password, oidc_provider_id, oidc_subject) "
            "VALUES (%s, %s, %s, %s, %s)",
            ("oidc_user", "oidc@example.com", "hash", provider_id, "sub_12345")
        )
    conn.commit()

    response = client.delete(
        f"/api/v1/auth/providers/{provider_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 409
    assert "linked user" in response.json()["detail"]


@pytest.mark.asyncio
async def test_test_provider_discovery(client, admin_token):
    """Test provider discovery endpoint."""
    create_resp = client.post(
        "/api/v1/auth/providers",
        json={
            "name": "Discovery Test",
            "kind": "oidc",
            "config": {
                "issuer": "https://keycloak.example.com/realms/test",
                "client_id": "test",
                "client_secret": "secret",
                "redirect_uri": "http://localhost:5173/auth/oidc/callback",
            }
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    provider_id = create_resp.json()["id"]

    # Mock httpx client
    mock_metadata = {
        "issuer": "https://keycloak.example.com/realms/test",
        "authorization_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/auth",
        "token_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/token",
        "userinfo_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/userinfo",
        "jwks_uri": "https://keycloak.example.com/realms/test/protocol/openid-connect/certs",
        "end_session_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/logout",
    }

    with patch("backend.app.api.routes.auth_providers.httpx.AsyncClient") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client_ctx.return_value.__aenter__.return_value = mock_client

        # Mock discovery response
        mock_disc_resp = AsyncMock()
        mock_disc_resp.status_code = 200
        mock_disc_resp.json.return_value = mock_metadata

        # Mock JWKS response
        mock_jwks_resp = AsyncMock()
        mock_jwks_resp.status_code = 200
        mock_jwks_resp.json.return_value = {"keys": []}

        mock_client.get.side_effect = [mock_disc_resp, mock_jwks_resp]

        response = client.post(
            f"/api/v1/auth/providers/{provider_id}/test",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["issuer"] == "https://keycloak.example.com/realms/test"
    assert data["jwks_uri"] == "https://keycloak.example.com/realms/test/protocol/openid-connect/certs"
    assert "authorization_endpoint" in data["discovered_endpoints"]
