"""Config CRUD endpoints."""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from .. import auth as auth_module
from ..db import execute, insert_and_return, query_all, query_one

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


# ─── Config test endpoint ────────────────────────────────────────────────────


@router.post(
    "/config/{config_id}/test",
    dependencies=[Depends(require_auth)],
)
async def test_config(config_id: str) -> dict[str, Any]:
    """Test cloud credentials without running an extraction."""
    row = query_one(
        "SELECT provider, credential_type, config FROM cloud_config WHERE id = %s",
        (config_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Configuration not found")

    provider = row["provider"]
    config = decrypt_config(row["config"])

    if provider == "azure":
        try:
            from azure.identity import AzureCliCredential, ClientSecretCredential

            cred_type = row.get("credential_type") or config.get("credential_type", "")
            if cred_type == "cli":
                credential = AzureCliCredential()
            else:
                tenant_id = config.get("tenant_id", "")
                client_id = config.get("client_id", "")
                client_secret = config.get("client_secret", "")
                if not all([tenant_id, client_id, client_secret]):
                    return {"ok": False, "provider": "azure", "error": "Missing tenant_id, client_id or client_secret"}
                credential = ClientSecretCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret,
                )

            token = credential.get_token("https://management.azure.com/.default")
            checks: dict[str, Any] = {"auth": "ok"}

            # Check Cost Management API access on the configured scope
            subscription_id = config.get("subscription_id")
            if subscription_id:
                from datetime import datetime, timedelta
                from datetime import timezone as tz

                from azure.mgmt.costmanagement import CostManagementClient
                from azure.mgmt.costmanagement.models import (
                    QueryDataset,
                    QueryDefinition,
                    QueryTimePeriod,
                    TimeframeType,
                )

                cm_client = CostManagementClient(credential=credential, subscription_id=subscription_id)

                resource_groups = config.get("resource_groups") or []
                scope_type = config.get("scope", "subscription")
                if resource_groups:
                    scope = f"/subscriptions/{subscription_id}/resourceGroups/{resource_groups[0]}"
                    checks["scope"] = scope
                elif scope_type == "subscription":
                    scope = f"/subscriptions/{subscription_id}"
                    checks["scope"] = scope
                else:
                    scope = f"/subscriptions/{subscription_id}"
                    checks["scope"] = scope

                # Minimal 1-day query — just validates permissions, discards rows
                now = datetime.now(tz.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                date_from = now - timedelta(days=1)
                try:
                    result = cm_client.query.usage(
                        scope=scope,
                        parameters=QueryDefinition(
                            type="ActualCost",
                            timeframe=TimeframeType.CUSTOM,
                            time_period=QueryTimePeriod(from_property=date_from, to=now),
                            dataset=QueryDataset(granularity="Daily", aggregation={}),
                        ),
                    )
                    row_count = len(result.rows) if result.rows else 0
                    checks["cost_management_api"] = "ok"
                    checks["sample_rows"] = row_count
                except Exception as cm_exc:
                    checks["cost_management_api"] = "failed"
                    checks["cost_management_error"] = str(cm_exc)

            return {
                "ok": checks.get("cost_management_api", "ok") != "failed",
                "provider": "azure",
                "token_expires_at": token.expires_on,
                "checks": checks,
            }
        except Exception as exc:
            return {"ok": False, "provider": "azure", "error": str(exc)}

    if provider == "gcp":
        try:
            from google.auth import default as google_auth_default
            from google.auth.transport.requests import Request

            kwargs: dict[str, Any] = {}
            project_id = config.get("project_id")
            if project_id:
                kwargs["quota_project_id"] = project_id

            creds, project = google_auth_default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"], **kwargs
            )
            if not creds.valid:
                creds.refresh(Request())
            return {
                "ok": True,
                "provider": "gcp",
                "details": f"Credentials valid, project={project}",
            }
        except Exception as exc:
            return {"ok": False, "provider": "gcp", "error": str(exc)}

    return {"ok": False, "provider": provider, "error": f"Test not implemented for provider '{provider}'"}


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



# ─── CLI-compatible /configs endpoints ───────────────────────────────────────

@router.get("/configs", dependencies=[Depends(require_auth)])
async def cli_config_list() -> dict[str, Any]:
    """CLI-compatible config list wrapper."""
    rows = query_all("SELECT id, provider, name, credential_type, config, created_at, updated_at FROM cloud_config ORDER BY provider, name")
    data = [
        {
            "id": r["id"],
            "provider": r["provider"],
            "name": r["name"],
            "credential_type": r["credential_type"],
            "service_category": r["credential_type"],
            "region": "",
            "last_updated": r["updated_at"].isoformat() if r["updated_at"] else None,
        }
        for r in rows
    ]
    return {"data": data, "total": len(data), "page": 1, "page_size": len(data), "has_next": False, "has_prev": False}

@router.get("/configs/{config_id}", dependencies=[Depends(require_auth)])
async def cli_config_get(config_id: str) -> dict[str, Any]:
    """CLI-compatible config get."""
    sql = "SELECT id, provider, name, credential_type, config, created_at, updated_at FROM cloud_config WHERE id = %s"
    r = query_one(sql, (config_id,))
    if not r:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {
        "id": r["id"],
        "provider": r["provider"],
        "name": r["name"],
        "credential_type": r["credential_type"],
        "service_category": r["credential_type"],
        "region": "",
        "last_updated": r["updated_at"].isoformat() if r["updated_at"] else None,
    }


# ─── CLI-compatibility /configs CUD wrappers ────────────────────────────────

import uuid as _uuid
from datetime import datetime as __dt, timezone as __tz
from pydantic import BaseModel as _BM

class _ConfigCreate(_BM):
    provider: str
    cloud_config: str | None = None
    service_category: str | None = None
    region: str | None = None

@router.post("/configs", dependencies=[Depends(require_auth)], status_code=201)
async def cli_configs_create(data: _ConfigCreate) -> dict[str, Any]:
    """CLI-compatible config create."""
    cfg_id = str(_uuid.uuid4())
    now = __dt.now(__tz.utc)
    cfg_dict: dict[str, Any] = {"provider": data.provider}
    if data.region:
        cfg_dict["region"] = data.region
    if data.service_category:
        cfg_dict["service_category"] = data.service_category
    if data.cloud_config:
        cfg_dict["cloud_config"] = data.cloud_config
    insert_and_return(
        "INSERT INTO cloud_config (id, provider, name, credential_type, config, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (cfg_id, data.provider, f"{data.provider} config", data.service_category or "unknown", cfg_dict, now, now),
    )
    return {
        "id": cfg_id,
        "provider": data.provider,
        "service_category": data.service_category or "",
        "region": data.region or "",
        "last_updated": now.isoformat(),
    }

@router.put("/configs/{config_id}", dependencies=[Depends(require_auth)])
async def cli_configs_update(config_id: str, data: _ConfigCreate) -> dict[str, Any]:
    """CLI-compatible config update."""
    existing = query_one("SELECT id FROM cloud_config WHERE id = %s", (config_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Configuration not found")
    now = __dt.now(__tz.utc)
    # Fetch existing config blob
    row = query_one("SELECT config FROM cloud_config WHERE id = %s", (config_id,))
    cfg = row["config"] if row and row.get("config") else {}
    if isinstance(cfg, str):
        try:
            import json as __json
            cfg = __json.loads(cfg)
        except Exception:
            cfg = {}
    if data.region:
        cfg["region"] = data.region
    if data.service_category:
        cfg["service_category"] = data.service_category
    if data.cloud_config:
        cfg["cloud_config"] = data.cloud_config
    execute(
        "UPDATE cloud_config SET provider = %s, config = %s, updated_at = %s WHERE id = %s",
        (data.provider, cfg, now, config_id),
    )
    return {
        "id": config_id,
        "provider": data.provider,
        "service_category": data.service_category or "",
        "region": data.region or "",
        "last_updated": now.isoformat(),
    }

@router.delete("/configs/{config_id}", dependencies=[Depends(require_auth)], status_code=204)
async def cli_configs_delete(config_id: str) -> None:
    """CLI-compatible config delete."""
    existing = query_one("SELECT id FROM cloud_config WHERE id = %s", (config_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Configuration not found")
    execute("DELETE FROM cloud_config WHERE id = %s", (config_id,))
