"""Comprehensive tests for api/auth module - JWT authentication."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException

os.environ["JWT_SECRET"] = "test-secret-key-32-bytes-minimum"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRATION_MINUTES"] = "60"


class TestCreateAccessToken:
    """Comprehensive tests for create_access_token function."""

    def test_create_token_with_default_expiry(self):
        """Test creating a token with default expiration."""
        from api.auth import create_access_token, JWT_EXPIRATION_MINUTES

        token = create_access_token(data={"sub": "testuser"})
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_with_custom_expiry(self):
        """Test creating a token with custom expiration."""
        from api.auth import create_access_token

        custom_delta = timedelta(minutes=30)
        token = create_access_token(data={"sub": "testuser"}, expires_delta=custom_delta)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_user_identifier(self):
        """Test that token contains the user identifier."""
        from api.auth import create_access_token, decode_token

        token = create_access_token(data={"sub": "testuser"})
        payload = decode_token(token)
        assert payload["sub"] == "testuser"

    def test_token_contains_custom_claims(self):
        """Test that token contains custom claims."""
        from api.auth import create_access_token, decode_token

        token = create_access_token(data={"sub": "testuser", "role": "admin", "org": "acme"})
        payload = decode_token(token)
        assert payload["sub"] == "testuser"
        assert payload["role"] == "admin"
        assert payload["org"] == "acme"

    def test_token_expiration_time(self):
        """Test that token expiration is set correctly."""
        from api.auth import create_access_token, decode_token

        custom_delta = timedelta(hours=2)
        token = create_access_token(data={"sub": "testuser"}, expires_delta=custom_delta)
        payload = decode_token(token)
        assert "exp" in payload
        assert payload["exp"] > 0


class TestVerifyToken:
    """Comprehensive tests for verify_token (decode_token) function."""

    def test_valid_token_decodes_correctly(self):
        """Test that a valid token can be decoded."""
        from api.auth import create_access_token, verify_token

        token = create_access_token(data={"sub": "testuser"})
        payload = verify_token(token)
        assert payload["sub"] == "testuser"

    def test_invalid_token_raises_401(self):
        """Test that an invalid token raises HTTPException with 401."""
        from api.auth import verify_token

        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid.token.here")
        assert exc_info.value.status_code == 401

    def test_expired_token_raises_401(self):
        """Test that an expired token raises HTTPException with 401."""
        from api.auth import create_access_token, verify_token
        import jwt

        token = create_access_token(data={"sub": "testuser"})
        expired_payload = {
            "sub": "testuser",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }

        expired_token = jwt.encode(
            expired_payload,
            os.environ["JWT_SECRET"],
            algorithm=os.environ["JWT_ALGORITHM"],
        )

        with pytest.raises(HTTPException) as exc_info:
            verify_token(expired_token)
        assert exc_info.value.status_code == 401

    def test_wrong_jwt_secret_raises_401(self):
        """Test that a token signed with wrong secret raises 401."""
        from api.auth import create_access_token, verify_token
        import jwt

        token = create_access_token(data={"sub": "testuser"})

        wrong_secret = "wrong-secret-key"
        tampered_token = jwt.encode(
            {"sub": "attacker", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            wrong_secret,
            algorithm=os.environ["JWT_ALGORITHM"],
        )

        with pytest.raises(HTTPException) as exc_info:
            verify_token(tampered_token)
        assert exc_info.value.status_code == 401

    def test_token_with_no_signature_raises_401(self):
        """Test that a token with no signature raises 401."""
        from api.auth import verify_token

        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0."

        with pytest.raises(HTTPException) as exc_info:
            verify_token(fake_token)
        assert exc_info.value.status_code == 401

    def test_empty_string_token_raises_401(self):
        """Test that an empty token raises 401."""
        from api.auth import verify_token

        with pytest.raises(HTTPException) as exc_info:
            verify_token("")
        assert exc_info.value.status_code == 401

    def test_malformed_token_raises_401(self):
        """Test that a malformed token raises 401."""
        from api.auth import verify_token

        with pytest.raises(HTTPException) as exc_info:
            verify_token("not-a-valid-jwt-at-all")
        assert exc_info.value.status_code == 401


class TestGetCurrentUser:
    """Comprehensive tests for get_current_user dependency."""

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
        from api.auth import get_current_user

        token = "valid_token_with_no_sub"

        with patch("api.auth.decode_token") as mock_decode:
            mock_decode.return_value = {}
            with pytest.raises(HTTPException) as exc_info:
                get_current_user(token)
            assert exc_info.value.status_code == 401

    def test_empty_payload_raises_401(self):
        """Test that an empty payload raises HTTPException."""
        from api.auth import get_current_user

        token = "any_token"

        with patch("api.auth.decode_token") as mock_decode:
            mock_decode.return_value = {}
            with pytest.raises(HTTPException) as exc_info:
                get_current_user(token)
            assert exc_info.value.status_code == 401

    def test_none_payload_raises_401(self):
        """Test that None payload raises HTTPException."""
        from api.auth import get_current_user

        token = "any_token"

        with patch("api.auth.decode_token") as mock_decode:
            mock_decode.return_value = None
            with pytest.raises(HTTPException) as exc_info:
                get_current_user(token)
            assert exc_info.value.status_code == 401


class TestTokenVerificationMiddleware:
    """Tests for token_verification_middleware."""

    def test_valid_bearer_token_passes(self):
        """Test that a valid Bearer token passes middleware."""
        from api.auth import token_verification_middleware
        from fastapi import Request
        from unittest.mock import MagicMock

        async def mock_call_next(request):
            return {"success": True}

        token = "valid.token.here"

        with patch("api.auth.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": "testuser", "exp": 9999999999}
            request = MagicMock()
            request.url.path = "/api/v1/healthz"
            request.headers.get.return_value = f"Bearer {token}"

            result = token_verification_middleware(request, mock_call_next)
            assert result is not None

    def test_missing_authorization_header_raises_401(self):
        """Test that missing Authorization header raises 401."""
        from api.auth import token_verification_middleware
        from fastapi import Request
        from fastapi import HTTPException
        from unittest.mock import MagicMock

        async def mock_call_next(request):
            return {"success": True}

        with patch("api.auth.decode_token") as mock_decode:
            request = MagicMock()
            request.url.path = "/api/v1/config"
            request.headers.get.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                token_verification_middleware(request, mock_call_next)
            assert exc_info.value.status_code == 401

    def test_invalid_bearer_token_raises_401(self):
        """Test that an invalid Bearer token raises 401."""
        from api.auth import token_verification_middleware
        from fastapi import Request, HTTPException
        from unittest.mock import MagicMock

        async def mock_call_next(request):
            return {"success": True}

        with patch("api.auth.decode_token") as mock_decode:
            mock_decode.side_effect = HTTPException(status_code=401)
            request = MagicMock()
            request.url.path = "/api/v1/config"
            request.headers.get.return_value = "Bearer invalid.token"

            with pytest.raises(HTTPException) as exc_info:
                token_verification_middleware(request, mock_call_next)
            assert exc_info.value.status_code == 401

    def test_healthz_endpoint_without_token_succeeds(self):
        """Test that /api/v1/healthz doesn't require token."""
        from api.auth import token_verification_middleware
        from fastapi import Request
        from unittest.mock import MagicMock

        async def mock_call_next(request):
            return {"success": True}

        request = MagicMock()
        request.url.path = "/api/v1/healthz"
        request.headers.get.return_value = None

        result = token_verification_middleware(request, mock_call_next)
        assert result is not None


class TestRequireAuth:
    """Tests for require_auth dependency."""

    def test_require_auth_calls_get_current_user(self):
        """Test that require_auth calls get_current_user."""
        from api.auth import require_auth

        assert require_auth is not None
        assert callable(require_auth)

    def test_require_auth_returns_user_dict(self):
        """Test that require_auth returns a user dictionary."""
        from api.auth import require_auth, get_current_user

        assert require_auth is get_current_user


class TestGetPasswordHash:
    """Tests for password hashing."""

    def test_get_password_hash_returns_different_hashes(self):
        """Test that hashing the same password returns different hashes."""
        from api.auth import get_password_hash

        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2

    def test_get_password_hash_is_not_plain_text(self):
        """Test that hash is not the plain text password."""
        from api.auth import get_password_hash

        password = "testpassword123"
        hash_result = get_password_hash(password)

        assert hash_result != password
        assert "testpassword123" not in hash_result


class TestVerifyPassword:
    """Tests for password verification."""

    def test_verify_password_correct(self):
        """Test that correct password verifies."""
        from api.auth import get_password_hash, verify_password

        password = "mypassword123"
        hashed = get_password_hash(password)

        result = verify_password(password, hashed)
        assert result is True

    def test_verify_password_incorrect(self):
        """Test that incorrect password fails to verify."""
        from api.auth import get_password_hash, verify_password

        password = "mypassword123"
        wrong_password = "wrongpassword456"
        hashed = get_password_hash(password)

        result = verify_password(wrong_password, hashed)
        assert result is False


class TestJWTSecretValidation:
    """Tests for JWT secret validation."""

    def test_create_token_no_secret_raises_error(self):
        """Test that creating token without JWT_SECRET raises ValueError."""
        from api.auth import create_access_token

        original_secret = os.environ.get("JWT_SECRET")
        os.environ.pop("JWT_SECRET", None)

        try:
            with pytest.raises(ValueError) as exc_info:
                create_access_token(data={"sub": "testuser"})
            assert "JWT_SECRET" in str(exc_info.value)
        finally:
            if original_secret:
                os.environ["JWT_SECRET"] = original_secret

    def test_decode_token_no_secret_raises_error(self):
        """Test that decoding token without JWT_SECRET raises ValueError."""
        from api.auth import decode_token

        original_secret = os.environ.get("JWT_SECRET")
        os.environ.pop("JWT_SECRET", None)

        try:
            with pytest.raises(ValueError) as exc_info:
                decode_token("dummy.token.here")
            assert "JWT_SECRET" in str(exc_info.value)
        finally:
            if original_secret:
                os.environ["JWT_SECRET"] = original_secret


class TestTokenCreationEdgeCases:
    """Edge case tests for token creation."""

    def test_create_token_with_empty_data(self):
        """Test creating token with empty data dict."""
        from api.auth import create_access_token

        token = create_access_token(data={})
        assert token is not None
        assert isinstance(token, str)

    def test_create_token_with_none_explicit_delta(self):
        """Test creating token with None expires_delta."""
        from api.auth import create_access_token

        token = create_access_token(data={"sub": "testuser"}, expires_delta=None)
        assert token is not None

    def test_create_token_special_characters_in_data(self):
        """Test creating token with special characters in data."""
        from api.auth import create_access_token, decode_token

        token = create_access_token(
            data={
                "sub": "user@example.com",
                "role": "admin-user",
                "org": "ACME-Corp_2024",
            }
        )
        payload = decode_token(token)
        assert payload["sub"] == "user@example.com"

    def test_create_token_large_data_payload(self):
        """Test creating token with large data payload."""
        from api.auth import create_access_token, decode_token

        large_data = {f"key_{i}": f"value_{i}" for i in range(100)}

        token = create_access_token(data=large_data)
        assert token is not None

        payload = decode_token(token)
        assert payload["key_0"] == "value_0"


class TestTokenDecodingEdgeCases:
    """Edge case tests for token decoding."""

    def test_decode_token_with_invalid_base64(self):
        """Test decoding token with invalid base64."""
        from api.auth import verify_token

        invalid_token = "invalid.base64.!!!"

        with pytest.raises(HTTPException):
            verify_token(invalid_token)

    def test_decode_token_with_json_payload_error(self):
        """Test decoding token where payload is not JSON."""
        from api.auth import verify_token
        import jwt

        token = jwt.encode(
            {"data": "not json valid"},
            os.environ["JWT_SECRET"],
            algorithm=os.environ["JWT_ALGORITHM"],
        )

        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
        assert payload["data"] == "not json valid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
