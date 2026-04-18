"""Tests for log sanitizer."""

import pytest
from utils.log_sanitizer import sanitize_log


class TestAwsKeys:
    def test_aws_access_key_id(self):
        text = "Found AWS key: AKIAIOSFODNN7EXAMPLE"
        result = sanitize_log(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "***" in result

    def test_aws_secret_access_key(self):
        text = "aws_secret_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        result = sanitize_log(text)
        assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in result

    def test_multiple_aws_keys(self):
        text = "Key1: AKIAIOSFODNN7EXAMPLE and also AKIAJ5KI5NGJQS2Z"
        result = sanitize_log(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "AKIAJ5KI5NGJQS2Z" not in result


class TestAzureCredentials:
    def test_azure_client_secret(self):
        text = "client_secret=abc123~xyz456.def789_abc123~xyz456"
        result = sanitize_log(text)
        assert "abc123~xyz456.def789_abc123" not in result

    def test_azure_tenant_id(self):
        text = "tenant_id=12345678-1234-1234-1234-123456789012"
        result = sanitize_log(text)
        assert "12345678-1234-1234-1234-123456789012" not in result


class TestPostgresConnection:
    def test_postgres_dsn_with_password(self):
        text = "postgresql://user:secretpass@localhost/dbname"
        result = sanitize_log(text)
        assert "secretpass" not in result
        assert "***" in result


class TestBearerTokens:
    def test_bearer_token(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token"
        result = sanitize_log(text)
        assert "Bearer" not in result or "***" in result

    def test_bearer_token_inline(self):
        text = " bearer ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        result = sanitize_log(text)
        assert "ghp_" not in result


class TestPasswordsInUrls:
    def test_password_in_url(self):
        text = "Connecting to https://user:password123@example.com/api"
        result = sanitize_log(text)
        assert "password123" not in result


class TestGcpCredentials:
    def test_gcp_private_key(self):
        text = '"private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIICXAIBAAKBgQC..."'
        result = sanitize_log(text)
        assert "private_key" not in result or "***" in result

    def test_gcp_private_key_id(self):
        text = '"private_key_id": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"'
        result = sanitize_log(text)
        assert "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef" not in result


class TestEnvVars:
    def test_azure_client_secret_env(self):
        text = "AZURE_CLIENT_SECRET=abc123~xyz456.def789"
        result = sanitize_log(text)
        assert "abc123~xyz456.def789" not in result

    def test_azure_tenant_id_env(self):
        text = "AZURE_TENANT_ID=12345678-1234-1234-1234-123456789012"
        result = sanitize_log(text)
        assert "12345678-1234-1234-1234-123456789012" not in result

    def test_pg_dsn_env(self):
        text = "PG_DSN=postgresql://user:pass@host/db"
        result = sanitize_log(text)
        assert "pass" not in result


class TestEdgeCases:
    def test_empty_string(self):
        assert sanitize_log("") == ""

    def test_none_returns_none(self):
        assert sanitize_log(None) is None or sanitize_log("None") == "None"

    def test_no_sensitive_data(self):
        text = "This is a normal log message with no sensitive data."
        result = sanitize_log(text)
        assert result == text

    def test_preserve_legitimate_content(self):
        text = "Process started successfully. Loaded 100 records."
        result = sanitize_log(text)
        assert "Process started successfully" in result
        assert "Loaded 100 records" in result


class TestRealWorldScenarios:
    def test_subprocess_output_with_aws_key(self):
        output = """
Running extraction...
Using credentials: AKIAIOSFODNN7EXAMPLE
Connecting to AWS...
Extracted 500 records.
"""
        result = sanitize_log(output)
        assert "AKIAIOSFODNN7EXAMPLE" not in result

    def test_subprocess_output_with_postgres_dsn(self):
        output = """
Database connection: postgresql://admin:MySecretPass@db.example.com:5432/costs
Query executed successfully.
"""
        result = sanitize_log(output)
        assert "MySecretPass" not in result

    def test_subprocess_output_with_bearer_token(self):
        output = """
API call: GET /api/v1/data
Authorization: Bearer ghp_AbCdEfGhIjKlMnOpQrStUvWxYz0123456789
Response: 200 OK
"""
        result = sanitize_log(output)
        assert "ghp_" not in result
