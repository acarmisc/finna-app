"""OIDC auth providers CRUD endpoints."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from utils.encryption import decrypt_config, encrypt_config

from .. import auth as api_auth
from ..db import execute, insert_and_return, query_all, query_one

require_admin = api_auth.require_admin
logger = logging.getLogger("api.auth_providers")

router = APIRouter()


class AuthProviderConfig(BaseModel):
    """OIDC provider configuration schema."""
    issuer: str
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: list[str] = Field(default_factory=lambda: ["openid", "profile", "email"])
    claim_mappings: dict[str, Any] = Field(default_factory=dict)
    auto_provision: bool = False
    allowed_email_domains: list[str] = Field(default_factory=list)


class AuthProviderInput(BaseModel):
    """Create/update provider request."""
    name: str
    kind: str = "oidc"
    enabled: bool = False
    config: AuthProviderConfig


class AuthProviderResponse(BaseModel):
    """Provider response (secrets masked)."""
    id: str
    name: str
    kind: str
    enabled: bool
    config: dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None
    last_test_at: Optional[str] = None
    last_test_ok: Optional[bool] = None


def _mask_provider_secrets(config: dict[str, Any]) -> dict[str, Any]:
    """Mask sensitive fields in provider config (allow-list pattern)."""
    if not config:
        return {}
    safe_fields = {
        "issuer", "client_id", "redirect_uri", "scopes", "claim_mappings",
        "auto_provision", "allowed_email_domains"
    }
    masked = {k: v for k, v in config.items() if k in safe_fields}
    return masked


@router.get("/auth/providers", dependencies=[Depends(require_admin)])
async def list_providers() -> list[AuthProviderResponse]:
    """List all OIDC providers (secrets masked)."""
    rows = query_all(
        """
        SELECT id, name, kind, enabled, config, created_at, updated_at,
               created_by, last_test_at, last_test_ok
        FROM auth_providers
        ORDER BY created_at DESC
        """
    )
    result = []
    for row in rows:
        config = decrypt_config(row["config"])
        masked = _mask_provider_secrets(config)
        result.append(
            AuthProviderResponse(
                id=row["id"],
                name=row["name"],
                kind=row["kind"],
                enabled=row["enabled"],
                config=masked,
                created_at=row["created_at"].isoformat() if row["created_at"] else None,
                updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
                created_by=row.get("created_by"),
                last_test_at=(
                    _last_test_at.isoformat() if _last_test_at is not None else None
                ),
                last_test_ok=row.get("last_test_ok"),
            )
            for row in rows
        )
    return result


@router.get("/auth/providers/{provider_id}", dependencies=[Depends(require_admin)])
async def get_provider(provider_id: str) -> AuthProviderResponse:
    """Get single provider (secrets masked)."""
    row = query_one(
        """
        SELECT id, name, kind, enabled, config, created_at, updated_at,
               created_by, last_test_at, last_test_ok
        FROM auth_providers
        WHERE id = %s
        """,
        (provider_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")

    config = decrypt_config(row["config"])
    masked = _mask_provider_secrets(config)
    return AuthProviderResponse(
        id=row["id"],
        name=row["name"],
        kind=row["kind"],
        enabled=row["enabled"],
        config=masked,
        created_at=row["created_at"].isoformat() if row["created_at"] else None,
        updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
        created_by=row.get("created_by"),
        last_test_at=_lat.isoformat() if (_lat := row.get("last_test_at")) is not None else None,
        last_test_ok=row.get("last_test_ok"),
    )


@router.post("/auth/providers", dependencies=[Depends(require_admin)])
async def create_provider(
    request: AuthProviderInput,
    user: dict[str, Any] = Depends(require_admin),
) -> AuthProviderResponse:
    """Create new OIDC provider."""
    provider_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Check for duplicate name
    existing = query_one("SELECT id FROM auth_providers WHERE lower(name) = lower(%s)", (request.name,))
    if existing:
        raise HTTPException(status_code=409, detail="Provider name already exists")

    # Encrypt config
    config_dict = request.config.model_dump()
    encrypted_config = encrypt_config(config_dict)

    insert_and_return(
        """
        INSERT INTO auth_providers (id, name, kind, enabled, config, created_at, updated_at, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (provider_id, request.name, request.kind, request.enabled, encrypted_config, now, now, user["username"]),
    )

    return AuthProviderResponse(
        id=provider_id,
        name=request.name,
        kind=request.kind,
        enabled=request.enabled,
        config=_mask_provider_secrets(config_dict),
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        created_by=user["username"],
    )


@router.put("/auth/providers/{provider_id}", dependencies=[Depends(require_admin)])
async def update_provider(provider_id: str, request: AuthProviderInput) -> AuthProviderResponse:
    """Update OIDC provider."""
    row = query_one("SELECT id, name FROM auth_providers WHERE id = %s", (provider_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Check for duplicate name (excluding self)
    if request.name != row["name"]:
        existing = query_one(
            "SELECT id FROM auth_providers WHERE lower(name) = lower(%s) AND id != %s",
            (request.name, provider_id),
        )
        if existing:
            raise HTTPException(status_code=409, detail="Provider name already exists")

    now = datetime.now(timezone.utc)
    config_dict = request.config.model_dump()
    encrypted_config = encrypt_config(config_dict)

    execute(
        """
        UPDATE auth_providers
        SET name = %s, kind = %s, enabled = %s, config = %s, updated_at = %s
        WHERE id = %s
        """,
        (request.name, request.kind, request.enabled, encrypted_config, now, provider_id),
    )

    return AuthProviderResponse(
        id=provider_id,
        name=request.name,
        kind=request.kind,
        enabled=request.enabled,
        config=_mask_provider_secrets(config_dict),
        created_at=row.get("created_at", now).isoformat() if isinstance(row.get("created_at"), datetime) else None,
        updated_at=now.isoformat(),
    )


@router.delete("/auth/providers/{provider_id}", dependencies=[Depends(require_admin)])
async def delete_provider(provider_id: str) -> dict[str, str]:
    """Delete OIDC provider (reject if users linked)."""
    row = query_one("SELECT id, name FROM auth_providers WHERE id = %s", (provider_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Check for linked users
    linked = query_one(
        "SELECT COUNT(*) as count FROM auth_users WHERE oidc_provider_id = %s",
        (provider_id,),
    )
    if linked and linked.get("count", 0) > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete provider with {linked['count']} linked user(s). Reassign users first."
        )

    execute("DELETE FROM auth_providers WHERE id = %s", (provider_id,))
    return {"message": f"Provider '{row['name']}' deleted"}


@router.post("/auth/providers/{provider_id}/test", dependencies=[Depends(require_admin)])
async def test_provider(provider_id: str) -> dict[str, Any]:
    """Test provider discovery and JWKS accessibility."""
    import httpx

    row = query_one(
        """
        SELECT config FROM auth_providers WHERE id = %s
        """,
        (provider_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")

    config = decrypt_config(row["config"])
    issuer = config.get("issuer", "")

    if not issuer:
        raise HTTPException(status_code=400, detail="Provider config missing issuer URL")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Discover metadata
            discovery_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
            disc_response = await client.get(discovery_url)
            if disc_response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Discovery failed: {disc_response.status_code}"
                )

            metadata = disc_response.json()
            jwks_uri = metadata.get("jwks_uri", "")

            if not jwks_uri:
                raise HTTPException(status_code=400, detail="No JWKS endpoint in discovery metadata")

            # Test JWKS fetch
            jwks_response = await client.get(jwks_uri)
            if jwks_response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"JWKS fetch failed: {jwks_response.status_code}"
                )

            # Update last_test
            now = datetime.now(timezone.utc)
            execute(
                "UPDATE auth_providers SET last_test_at = %s, last_test_ok = %s WHERE id = %s",
                (now, True, provider_id),
            )

            return {
                "success": True,
                "issuer": issuer,
                "jwks_uri": jwks_uri,
                "discovered_endpoints": {
                    "authorization_endpoint": metadata.get("authorization_endpoint"),
                    "token_endpoint": metadata.get("token_endpoint"),
                    "userinfo_endpoint": metadata.get("userinfo_endpoint"),
                    "end_session_endpoint": metadata.get("end_session_endpoint"),
                }
            }

    except httpx.RequestError as e:
        execute(
            "UPDATE auth_providers SET last_test_at = %s, last_test_ok = %s WHERE id = %s",
            (datetime.now(timezone.utc), False, provider_id),
        )
        raise HTTPException(status_code=400, detail=f"Discovery error: {str(e)}")
