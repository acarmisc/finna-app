"""Tests for log sanitizer."""

from backend.utils.log_sanitizer import sanitize_log


def test_aws_access_key_id():
    text = "Found AWS key: AKIAIOSFODNN7EXAMPLE"
    result = sanitize_log(text)
    assert "AKIAIOSFODNN7EXAMPLE" not in result
    assert "***" in result


def test_aws_secret_access_key():
    text = "aws_secret_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    result = sanitize_log(text)
    assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in result


def test_multiple_aws_keys():
    text = "Key1: AKIAIOSFODNN7EXAMPLE and also AKIAJ5KI5NGJQS2Z"
    result = sanitize_log(text)
    assert "AKIAIOSFODNN7EXAMPLE" not in result
    assert "AKIAJ5KI5NGJQS2Z" not in result


def test_azure_client_secret():
    text = "client_secret=abc123~xyz456.def789_abc123~xyz456"
    result = sanitize_log(text)
    assert "abc123~xyz456.def789_abc123" not in result


def test_azure_tenant_id():
    text = "tenant_id=12345678-1234-1234-1234-123456789012"
    result = sanitize_log(text)
    assert "12345678-1234-1234-1234-123456789012" not in result


def test_postgres_dsn_with_password():
    text = "postgresql://user:secretpass@localhost/dbname"
    result = sanitize_log(text)
    assert "secretpass" not in result
    assert "***" in result


def test_bearer_token():
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token"
    result = sanitize_log(text)
    assert "Bearer" not in result or "***" in result


def test_bearer_token_inline():
    text = " bearer ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    result = sanitize_log(text)
    assert "ghp_" not in result


def test_password_in_url():
    text = "Connecting to https://user:password123@example.com/api"
    result = sanitize_log(text)
    assert "password123" not in result


def test_gcp_private_key():
    text = '"private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIICXAIBAAKBgQC..."'
    result = sanitize_log(text)
    assert "private_key" not in result or "***" in result


def test_gcp_private_key_id():
    text = '"private_key_id": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"'
    result = sanitize_log(text)
    assert "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef" not in result


def test_azure_client_secret_env():
    text = "AZURE_CLIENT_SECRET=abc123~xyz456.def789"
    result = sanitize_log(text)
    assert "abc123~xyz456.def789" not in result


def test_azure_tenant_id_env():
    text = "AZURE_TENANT_ID=12345678-1234-1234-1234-123456789012"
    result = sanitize_log(text)
    assert "12345678-1234-1234-1234-123456789012" not in result


def test_pg_dsn_env():
    text = "PG_DSN=postgresql://user:pass@host/db"
    result = sanitize_log(text)
    assert "pass" not in result


def test_empty_string():
    assert sanitize_log("") == ""


def test_none_returns_none():
    assert sanitize_log(None) is None or sanitize_log("None") == "None"


def test_no_sensitive_data():
    text = "This is a normal log message with no sensitive data."
    result = sanitize_log(text)
    assert result == text


def test_preserve_legitimate_content():
    text = "Process started successfully. Loaded 100 records."
    result = sanitize_log(text)
    assert "Process started successfully" in result
    assert "Loaded 100 records" in result


def test_subprocess_output_with_aws_key():
    output = """
Running extraction...
Using credentials: AKIAIOSFODNN7EXAMPLE
Connecting to AWS...
Extracted 500 records.
"""
    result = sanitize_log(output)
    assert "AKIAIOSFODNN7EXAMPLE" not in result


def test_subprocess_output_with_postgres_dsn():
    output = """
Database connection: postgresql://admin:MySecretPass@db.example.com:5432/costs
Query executed successfully.
"""
    result = sanitize_log(output)
    assert "MySecretPass" not in result


def test_subprocess_output_with_bearer_token():
    output = """
API call: GET /api/v1/data
Authorization: Bearer ghp_AbCdEfGhIjKlMnOpQrStUvWxYz0123456789
Response: 200 OK
"""
    result = sanitize_log(output)
    assert "ghp_" not in result
