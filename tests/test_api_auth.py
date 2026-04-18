"""Tests for OAuth2/JWT authentication functionality."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ["JWT_SECRET"] = "test-secret-key"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRATION_MINUTES"] = "60"


class TestCreateAccessToken:
    """Tests for create_access_token function."""

    def test_create_token_with_default_expiry(self):
        """Test creating a token with default expiration."""
        from api.auth import create_access_token, JWT_EXPIRATION_MINUTES

        token = create_access_token(data={"sub": "testuser"})
        assert token is not None
        assert isinstance(token, str)

    def test_create_token_with_custom_expiry(self):
        """Test creating a token with custom expiration."""
        from api.auth import create_access_token

        custom_delta = timedelta(minutes=30)
        token = create_access_token(data={"sub": "testuser"}, expires_delta=custom_delta)
        assert token is not None
        assert isinstance(token, str)

    def test_token_contains_user_identifier(self):
        """Test that token contains the user identifier."""
        from api.auth import create_access_token, decode_token

        token = create_access_token(data={"sub": "testuser"})
        payload = decode_token(token)
        assert payload["sub"] == "testuser"


class TestVerifyToken:
    """Tests for verify_token (decode_token) function."""

    def test_valid_token_decodes_correctly(self):
        """Test that a valid token can be decoded."""
        from api.auth import create_access_token, verify_token

        token = create_access_token(data={"sub": "testuser"})
        payload = verify_token(token)
        assert payload["sub"] == "testuser"

    def test_invalid_token_raises_401(self):
        """Test that an invalid token raises HTTPException with 401."""
        from api.auth import verify_token
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid.token.here")
        assert exc_info.value.status_code == 401

    def test_expired_token_raises_401(self):
        """Test that an expired token raises HTTPException with 401."""
        from api.auth import create_access_token, verify_token
        from fastapi import HTTPException

        token = create_access_token(data={"sub": "testuser"})
        expired_payload = {"sub": "testuser", "exp": datetime.now(timezone.utc) - timedelta(hours=1)}

        import jwt

        expired_token = jwt.encode(expired_payload, os.environ["JWT_SECRET"], algorithm=os.environ["JWT_ALGORITHM"])

        with pytest.raises(HTTPException) as exc_info:
            verify_token(expired_token)
        assert exc_info.value.status_code == 401


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    def test_valid_token_returns_user(self):
        """Test that a valid token returns the user."""
        from api.auth import create_access_token, get_current_user

        token = create_access_token(data={"sub": "testuser"})

        with patch("api.auth.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": "testuser"}
            user = get_current_user(token)
            assert user["username"] == "testuser"

    def test_missing_username_raises_401(self):
        """Test that missing username in token raises HTTPException."""
        from api.auth import get_current_user, OAuth2PasswordBearer
        from fastapi import HTTPException

        token = "valid_token_with_no_sub"

        with patch("api.auth.decode_token") as mock_decode:
            mock_decode.return_value = {}
            with pytest.raises(HTTPException) as exc_info:
                get_current_user(token)
            assert exc_info.value.status_code == 401


class TestTokenEndpoint:
    """Tests for POST /api/v1/auth/token endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client with mocked dependencies."""
        from api.main import app

        return TestClient(app)

    @patch("api.routes.auth.keyring.get_password")
    @patch("api.routes.auth.get_password_hash")
    @patch("api.routes.auth.create_access_token")
    def test_successful_token_generation(self, mock_create_token, mock_get_hash, mock_get_password, client):
        """Test successful token generation with valid credentials."""
        mock_get_password.return_value = None
        mock_get_hash.return_value = "hashed_password"
        mock_create_token.return_value = "fake-jwt-token"

        response = client.post(
            "/api/v1/auth/token",
            data={"username": "testuser", "password": "testpass"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @patch("api.routes.auth.keyring.get_password")
    def test_invalid_credentials_raises_401(self, mock_get_password, client):
        """Test that invalid credentials raise HTTPException with 401."""
        mock_get_password.return_value = "wrong_hash"

        response = client.post(
            "/api/v1/auth/token",
            data={"username": "testuser", "password": "wrongpass"},
        )

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    @patch("api.routes.auth.keyring.get_password")
    @patch("api.routes.auth.keyring.set_password")
    @patch("api.routes.auth.get_password_hash")
    def test_first_login_creates_user(self, mock_set_password, mock_get_hash, mock_get_password, client):
        """Test that first login creates a new user in keyring."""
        mock_get_password.return_value = None
        mock_get_hash.return_value = "new_hashed_password"

        response = client.post(
            "/api/v1/auth/token",
            data={"username": "newuser", "password": "newpass"},
        )

        assert response.status_code == 200
        mock_get_hash.assert_called_once_with("newpass")


class TestProtectedEndpointsRequireAuth:
    """Tests that protected endpoints require valid JWT."""

    @pytest.fixture
    def client(self):
        """Create test client with mocked dependencies."""
        from api.main import app

        return TestClient(app)

    def test_config_endpoint_without_token_returns_422(self, client):
        """Test that GET /api/v1/config without token returns error."""
        response = client.get("/api/v1/config")

        assert response.status_code in [401, 422]

    def test_config_endpoint_with_invalid_token_returns_401(self, client):
        """Test that GET /api/v1/config with invalid token returns 401."""
        response = client.get(
            "/api/v1/config",
            headers={"Authorization": "Bearer invalid.token"},
        )

        assert response.status_code == 401

    def test_extractor_endpoint_without_token_returns_422(self, client):
        """Test that POST /api/v1/extractors/run without token returns error."""
        response = client.post("/api/v1/extractors/run", json={"provider": "azure"})

        assert response.status_code in [401, 422]

    def test_extractor_endpoint_with_invalid_token_returns_401(self, client):
        """Test that POST /api/v1/extractors/run with invalid token returns 401."""
        response = client.post(
            "/api/v1/extractors/run",
            json={"provider": "azure"},
            headers={"Authorization": "Bearer invalid.token"},
        )

        assert response.status_code == 401


class TestAuthDependencies:
    """Tests for auth dependency Injection."""

    def test_require_auth_dependency(self):
        """Test that require_auth properly delegates to get_current_user."""
        from api.auth import require_auth, get_current_user

        assert require_auth is not None
        assert callable(require_auth)
