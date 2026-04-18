"""Config CRUD endpoints."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Response
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.db import execute, insert_and_return, query_one, query_all
from api.models import (
    CloudConfigCreate,
    CloudConfigResponse,
    CloudConfigUpdate,
    CredentialType,
    Provider,
)

router = APIRouter()

_limiter = Limiter(key_func=get_remote_address)

_rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
_rate_limit_per_hour = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))


def _mask_secrets(config: dict[str, Any]) -> dict[str, Any]:
    """Mask sensitive fields in config for response."""
    masked = config.copy()
    sensitive_fields = ["client_secret", "key_file_content"]
    for field in sensitive_fields:
        if field in masked:
            masked[field] = "***REDACTED***"
    return masked


@router.get("/config", response_model=list[CloudConfigResponse], dependencies=[_limiter.limit(f"{_rate_limit_per_minute}/{_rate_limit_per_hour}")])
async def list_configs() -> list[dict[str, Any]]:
    """List all cloud configurations."""
    sql = """
        SELECT id, provider, name, credential_type, config, created_at, updated_at
        FROM cloud_config
        ORDER BY provider, name
    """
    results = query_all(sql)
    return [
        {
            "id": r["id"],
            "provider": r["provider"],
            "name": r["name"],
            "credential_type": r["credential_type"],
            "config": _mask_secrets(r["config"]),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in results
    ]


@router.post("/config", response_model=CloudConfigResponse, status_code=201, dependencies=[_limiter.limit(f"{_rate_limit_per_minute}/{_rate_limit_per_hour}")])
async def create_config(data: CloudConfigCreate) -> dict[str, Any]:
    """Create a new cloud configuration."""
    config_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    sql = """
        INSERT INTO cloud_config (id, provider, name, credential_type, config, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    params = (
        config_id,
        data.provider.value,
        data.name,
        data.credential_type.value,
        data.config,
        now,
        now,
    )

    insert_and_return(sql, params)

    return {
        "id": config_id,
        "provider": data.provider.value,
        "name": data.name,
        "credential_type": data.credential_type.value,
        "config": _mask_secrets(data.config),
        "created_at": now,
        "updated_at": now,
    }


@router.get("/config/{config_id}", response_model=CloudConfigResponse, dependencies=[_limiter.limit(f"{_rate_limit_per_minute}/{_rate_limit_per_hour}")])
async def get_config(config_id: str) -> dict[str, Any]:
    """Get a cloud configuration by ID."""
    sql = """
        SELECT id, provider, name, credential_type, config, created_at, updated_at
        FROM cloud_config
        WHERE id = %s
    """
    result = query_one(sql, (config_id,))
    if not result:
        raise HTTPException(status_code=404, detail="Configuration not found")

    return {
        "id": result["id"],
        "provider": result["provider"],
        "name": result["name"],
        "credential_type": result["credential_type"],
        "config": _mask_secrets(result["config"]),
        "created_at": result["created_at"],
        "updated_at": result["updated_at"],
    }


@router.put("/config/{config_id}", response_model=CloudConfigResponse, dependencies=[_limiter.limit(f"{_rate_limit_per_minute}/{_rate_limit_per_hour}")])
async def update_config(config_id: str, data: CloudConfigUpdate) -> dict[str, Any]:
    """Update a cloud configuration."""
    # Build dynamic update
    updates = []
    params = []

    if data.name is not None:
        updates.append("name = %s")
        params.append(data.name)
    if data.credential_type is not None:
        updates.append("credential_type = %s")
        params.append(data.credential_type.value)
    if data.config is not None:
        updates.append("config = %s")
        params.append(data.config)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = %s")
    params.append(datetime.now(timezone.utc))
    params.append(config_id)

    sql = f"""
        UPDATE cloud_config
        SET {", ".join(updates)}
        WHERE id = %s
        RETURNING id, provider, name, credential_type, config, created_at, updated_at
    """

    result = query_one(sql, tuple(params))
    if not result:
        raise HTTPException(status_code=404, detail="Configuration not found")

    return {
        "id": result["id"],
        "provider": result["provider"],
        "name": result["name"],
        "credential_type": result["credential_type"],
        "config": _mask_secrets(result["config"]),
        "created_at": result["created_at"],
        "updated_at": result["updated_at"],
    }


@router.delete("/config/{config_id}", status_code=204, dependencies=[_limiter.limit(f"{_rate_limit_per_minute}/{_rate_limit_per_hour}")])
async def delete_config(config_id: str) -> None:
    """Delete a cloud configuration."""
    sql = "DELETE FROM cloud_config WHERE id = %s"
    execute(sql, (config_id,))


@router.get("/config/provider/{provider}", response_model=list[CloudConfigResponse], dependencies=[_limiter.limit(f"{_rate_limit_per_minute}/{_rate_limit_per_hour}")])
async def list_configs_by_provider(provider: str) -> list[dict[str, Any]]:
    """List configurations for a specific provider."""
    sql = """
        SELECT id, provider, name, credential_type, config, created_at, updated_at
        FROM cloud_config
        WHERE provider = %s
        ORDER BY name
    """
    results = query_all(sql, (provider,))
    return [
        {
            "id": r["id"],
            "provider": r["provider"],
            "name": r["name"],
            "credential_type": r["credential_type"],
            "config": _mask_secrets(r["config"]),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in results
    ]
