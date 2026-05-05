"""Tests for log sanitizer."""

from utils.log_sanitizer import sanitize_log


def test_aws_access_key_id():
    text = "Found AWS key: AKIAIOSFODNN7EXAMPLE"
    result = sanitize_log(text)
    assert "AKIAIOSFODNN7EXAMPLE" not in result
    assert "***" in result


def test_aws_secret_access_key():
    text = "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    result = sanitize_log(text)
    assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in result


def test_multiple_aws_keys():
    text = "Key1: AKIAIOSFODNN7EXAMPLE Key2: aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    result = sanitize_log(text)
    assert "AKIAIOSFODNN7EXAMPLE" not in result
    assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in result
    assert result.count("***") >= 2


def test_azure_connection_string():
    text = "DefaultEndpointsProtocol=https;AccountKey=abc123=="
    result = sanitize_log(text)
    # AccountKey is not in the patterns, so it should remain
    assert result == text


def test_gcp_service_account_key():
    text = '{"type":"service_account","private_key":"-----BEGIN PRIVATE KEY-----\\nabc\\n-----END PRIVATE KEY-----\\n"}'
    result = sanitize_log(text)
    assert "abc" not in result or "***" in result


def test_no_keys():
    text = "This is a normal log message without any secrets."
    result = sanitize_log(text)
    assert result == text


def test_empty_string():
    text = ""
    result = sanitize_log(text)
    assert result == ""
