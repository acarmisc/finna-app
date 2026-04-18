"""Integration tests for subproces log sanitization with all 18 patterns."""

from __future__ import annotations

import pytest

from utils.log_sanitizer import sanitize_log, _SENSITIVE_PATTERNS


class TestAllSanitizationPatterns:
    """Test all sanitization patterns defined in log_sanitizer.py."""

    def test_aws_access_key_pattern_count(self):
        """Test AWS Access Key ID pattern matches."""
        pattern_name = "AWS Access Key ID"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_aws_secret_access_key_pattern_count(self):
        """Test AWS Secret Access Key pattern matches."""
        pattern_name = "AWS Secret Access Key"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_azure_client_secret_pattern_count(self):
        """Test Azure Client Secret pattern matches."""
        pattern_name = "Azure Client Secret"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_azure_tenant_id_pattern_count(self):
        """Test Azure Tenant ID pattern matches."""
        pattern_name = "Azure Tenant ID"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_postgresql_dsn_pattern_count(self):
        """Test PostgreSQL DSN pattern matches."""
        pattern_name = "PostgreSQL DSN"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_bearer_token_pattern_count(self):
        """Test Bearer Token pattern matches."""
        pattern_name = "Bearer Token"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_authorization_header_pattern_count(self):
        """Test Authorization Header pattern matches."""
        pattern_name = "Authorization Header"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_api_key_pattern_count(self):
        """Test API Key pattern matches."""
        pattern_name = "API Key"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_password_in_url_pattern_count(self):
        """Test Password in URL pattern matches."""
        pattern_name = "Password in URL"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_gcp_private_key_pattern_count(self):
        """Test GCP Private Key pattern matches."""
        pattern_name = "GCP Service Account JSON"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_gcp_private_key_id_pattern_count(self):
        """Test GCP Private Key ID pattern matches."""
        pattern_name = "GCP Private Key ID"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_azure_client_secret_env_pattern_count(self):
        """Test AZURE_CLIENT_SECRET env var pattern matches."""
        pattern_name = "AZURE_CLIENT_SECRET env var"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_azure_tenant_id_env_pattern_count(self):
        """Test AZURE_TENANT_ID env var pattern matches."""
        pattern_name = "AZURE_TENANT_ID in env"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_azure_client_id_env_pattern_count(self):
        """Test AZURE_CLIENT_ID env var pattern matches."""
        pattern_name = "AZURE_CLIENT_ID in env"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_gcp_project_env_pattern_count(self):
        """Test GCP_PROJECT env var pattern matches."""
        pattern_name = "GCP_PROJECT env var"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_pg_dsn_env_pattern_count(self):
        """Test PG_DSN env var pattern matches."""
        pattern_name = "PG_DSN"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_postgres_password_pattern_count(self):
        """Test Postgres Password in DSN pattern matches."""
        pattern_name = "PostgreSQL Password in DSN"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_generic_secret_pattern_count(self):
        """Test Generic Secret pattern matches."""
        pattern_name = "Generic Secret"
        matching_patterns = [name for name, _ in _SENSITIVE_PATTERNS if name == pattern_name]

        assert len(matching_patterns) == 1

    def test_total_pattern_count(self):
        """Test total number of patterns is 18."""
        assert len(_SENSITIVE_PATTERNS) == 18


class TestPatternSanitization:
    """Test specific pattern sanitization."""

    def test_aws_access_key_sanitized(self):
        """Test AWS Access Key ID is sanitized."""
        text = "Key: AKIAIOSFODNN7EXAMPLE"
        result = sanitize_log(text)

        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "***" in result

    def test_aws_secret_key_sanitized(self):
        """Test AWS Secret Access Key is sanitized."""
        text = "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        result = sanitize_log(text)

        assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in result

    def test_azure_client_secret_sanitized(self):
        """Test Azure Client Secret is sanitized."""
        text = "client_secret=abc123def456ghi789"
        result = sanitize_log(text)

        assert "abc123def456ghi789" not in result

    def test_azure_tenant_id_sanitized(self):
        """Test Azure Tenant ID is sanitized."""
        text = "tenant_id=12345678-1234-1234-1234-123456789012"
        result = sanitize_log(text)

        assert "12345678-1234-1234-1234-123456789012" not in result

    def test_postgresql_dsn_sanitized(self):
        """Test PostgreSQL DSN is sanitized."""
        text = "postgresql://user:password123@localhost:5432/mydb"
        result = sanitize_log(text)

        assert "password123" not in result
        assert "***" in result

    def test_bearer_token_sanitized(self):
        """Test Bearer token is sanitized."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        result = sanitize_log(text)

        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "***" in result

    def test_password_in_url_sanitized(self):
        """Test password in URL is sanitized."""
        text = "https://user:secretpass@example.com/api"
        result = sanitize_log(text)

        assert "secretpass" not in result

    def test_gcp_private_key_sanitized(self):
        """Test GCP private key is sanitized."""
        text = '"private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIICXAIBAAKBgQC...'
        result = sanitize_log(text)

        assert "-----BEGIN RSA PRIVATE KEY-----" not in result
        assert "***" in result

    def test_gcp_private_key_id_sanitized(self):
        """Test GCP private key ID is sanitized."""
        text = '"private_key_id": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"'
        result = sanitize_log(text)

        assert "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef" not in result

    def test_azure_env_vars_sanitized(self):
        """Test Azure environment variables are sanitized."""
        text = "AZURE_CLIENT_SECRET=abc123def456\nAZURE_TENANT_ID=12345678-1234-1234-1234-123456789012"
        result = sanitize_log(text)

        assert "abc123def456" not in result
        assert "12345678-1234-1234-1234-123456789012" not in result

    def test_pg_dsn_sanitized(self):
        """Test PG_DSN is sanitized."""
        text = "PG_DSN=postgresql://user:pass@host:5432/db"
        result = sanitize_log(text)

        assert "pass" not in result

    def test_generic_secret_sanitized(self):
        """Test generic secret pattern is sanitized."""
        text = 'secret = "my-super-secret-password-123456789"'
        result = sanitize_log(text)

        assert "my-super-secret-password-123456789" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
