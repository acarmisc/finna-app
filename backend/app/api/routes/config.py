"""Config CRUD endpoints."""

from __future__ import annotations

import sys
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..db import insert_and_return, query_all, query_one, execute
from .. import auth as auth_module
require_auth = auth_module.require_auth
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".."))
from utils.encryption import decrypt_config, encrypt_config

from ..models import (
    CloudConfigCreate,
    CloudConfigResponse,
    CloudConfigUpdate,
)

router = APIRouter()


def _mask_secrets(config: dict[str, Any]) -> dict[str, Any]:
    masked = config.copy()
    sensitive_fields = ["client_secret", "key_file_content"]
    for field in sensitive_fields:
        if field in masked:
            masked[field] = "***REDACTED***"
    return masked


@router.get(
    "/config",
    response_model=list[CloudConfigResponse],
    dependencies=[Depends(require_auth)],
)
async def list_configs() -> list[dict[str, Any]]:
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
            "config": _mask_secrets(decrypt_config(r["config"])),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in results
    ]


@router.post(
    "/config",
    response_model=CloudConfigResponse,
    status_code=201,
    dependencies=[Depends(require_auth)],
)
async def create_config(data: CloudConfigCreate) -> dict[str, Any]:
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
        encrypt_config(data.config),
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


# ─── Projects endpoints ──────────────────────────────────────────────────────


@router.get(
    "/config/projects",
    dependencies=[Depends(require_auth)],
)
async def list_projects() -> list[dict[str, Any]]:
    """List all projects."""
    sql = "SELECT id, name, slug, owner, cost_center, budget_cap, mtd, tags, created_at, note FROM fin_projects ORDER BY name"
    rows = query_all(sql)
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "slug": r["slug"],
            "owner": r["owner"],
            "cost_center": r["cost_center"],
            "budget_cap": float(r["budget_cap"]) if r["budget_cap"] else None,
            "mtd": float(r["mtd"]) if r["mtd"] else 0.0,
            "tags": r["tags"] or {},
            "created": r["created_at"].isoformat() if r["created_at"] else None,
            "note": r.get("note", ""),
        }
        for r in rows
    ]


@router.post(
    "/config/projects",
    status_code=201,
    dependencies=[Depends(require_auth)],
)
async def create_project(data: dict[str, Any]) -> dict[str, Any]:
    """Create a new project."""
    from ..db import insert_and_return
    config_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    name = data.get("name", "Untitled")
    sql = """
        INSERT INTO fin_projects (id, name, slug, owner, cost_center, budget_cap, mtd, tags, created_at, note)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    slug = data.get("slug", name.lower().replace(" ", "-")[:20])
    insert_and_return(
        sql,
        (
            config_id,
            name,
            slug,
            data.get("owner", ""),
            data.get("cost_center", ""),
            data.get("budget_cap", 0),
            0,
            data.get("tags", {}),
            now,
            data.get("note", ""),
        ),
    )
    return {
        "id": config_id,
        "name": name,
        "slug": slug,
        "owner": data.get("owner", ""),
        "cost_center": data.get("cost_center", ""),
        "budget_cap": data.get("budget_cap", 0),
        "mtd": 0.0,
        "tags": data.get("tags", {}),
        "created": now.isoformat(),
        "note": data.get("note", ""),
    }


@router.get(
    "/config/provider/{provider}",
    response_model=list[CloudConfigResponse],
    dependencies=[Depends(require_auth)],
)
async def list_configs_by_provider(provider: str) -> list[dict[str, Any]]:
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
            "config": _mask_secrets(decrypt_config(r["config"])),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in results
    ]


# ─── Config by ID endpoints (must come after specific routes) ────────────────


@router.get(
    "/config/{config_id}",
    response_model=CloudConfigResponse,
    dependencies=[Depends(require_auth)],
)
async def get_config(config_id: str) -> dict[str, Any]:
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
        "config": _mask_secrets(decrypt_config(result["config"])),
        "created_at": result["created_at"],
        "updated_at": result["updated_at"],
    }


@router.put(
    "/config/{config_id}",
    response_model=CloudConfigResponse,
    dependencies=[Depends(require_auth)],
)
async def update_config(config_id: str, data: CloudConfigUpdate) -> dict[str, Any]:
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
        params.append(encrypt_config(data.config))

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
        "config": _mask_secrets(decrypt_config(result["config"])),
        "created_at": result["created_at"],
        "updated_at": result["updated_at"],
    }


@router.delete(
    "/config/{config_id}",
    status_code=204,
    dependencies=[Depends(require_auth)],
)
async def delete_config(config_id: str) -> None:
    sql = "DELETE FROM cloud_config WHERE id = %s"
    execute(sql, (config_id,))

