"""Log sanitization utilities to prevent credential leakage."""

from __future__ import annotations

import re

SANITIZE_REPLACEMENT = "***"

_SENSITIVE_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "AWS Access Key ID",
        re.compile(r"\bAKIA[0-9A-Z]{4,}\b", re.IGNORECASE),
    ),
    (
        "AWS Secret Access Key",
        re.compile(r"(?i)(aws_secret_access_key|aws_secret_key|secret_key)\s*=\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?"),
    ),
    (
        "Azure Client Secret",
        re.compile(r"(?i)(client_secret|azure_client_secret)\s*=\s*['\"]?([A-Za-z0-9~._-]{10,})['\"]?"),
    ),
    (
        "Azure Tenant ID",
        re.compile(r"(?i)(tenant_id|azure_tenant_id)\s*=\s*['\"]?([0-9a-f-]{36})['\"]?"),
    ),
    (
        "PostgreSQL DSN",
        re.compile(r"postgresql://[^:]+:([^@]+)@[^/]+/\w+"),
    ),
    (
        "PostgreSQL Password in DSN",
        re.compile(r"(?i)(password=|pwd=)([^;@\s]+)"),
    ),
    (
        "Bearer Token",
        re.compile(r"(?i)bearer\s+[A-Za-z0-9_.~-]+\b"),
    ),
    (
        "Authorization Header",
        re.compile(r"(?i)authorization\s*:\s*Bearer\s+[A-Za-z0-9_.~-]+\b"),
    ),
    (
        "API Key",
        re.compile(r"(?i)(api_key|apikey|api-key)\s*=\s*['\"]?([A-Za-z0-9_-]{20,})['\"]?"),
    ),
    (
        "Password in URL",
        re.compile(r"://[^:]+:([^@]+)@"),
    ),
    (
        "GCP Service Account JSON",
        re.compile(r'"private_key":\s*"[^"]+"'),
    ),
    (
        "GCP Private Key ID",
        re.compile(r'"private_key_id":\s*"[0-9a-f]{64}"'),
    ),
    (
        "AZURE_CLIENT_SECRET env var",
        re.compile(r"AZURE_CLIENT_SECRET=[^\s]+"),
    ),
    (
        "AZURE_TENANT_ID in env",
        re.compile(r"AZURE_TENANT_ID=[0-9a-f-]+\b"),
    ),
    (
        "AZURE_CLIENT_ID in env",
        re.compile(r"AZURE_CLIENT_ID=[0-9a-f-]+\b"),
    ),
    (
        "GCP_PROJECT env var",
        re.compile(r"GCP_PROJECT=[^\s]+"),
    ),
    (
        "PG_DSN",
        re.compile(r"PG_DSN=[^\s]+"),
    ),
    (
        "Generic Secret",
        re.compile(r"(?i)(secret|password|token|key)\s*=\s*['\"][^'\"]{8,}['\"]"),
    ),
]


def sanitize_log(text: str) -> str:
    """Sanitize sensitive data from log output.

    Args:
        text: The log text to sanitize.

    Returns:
        Sanitized text with sensitive data replaced.
    """
    if not text:
        return text

    result = text
    for name, pattern in _SENSITIVE_PATTERNS:
        result = pattern.sub(SANITIZE_REPLACEMENT, result)

    return result
