"""Auth endpoints — login and cloud credential registration."""

from __future__ import annotations

import base64
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".."))
from .. import auth as api_auth
from ..db import insert_and_return, query_one

require_auth = api_auth.require_auth
logger = logging.getLogger("api.auth")

router = APIRouter()


class TokenRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/token")
async def login_token(req: TokenRequest) -> dict[str, Any]:
    """Authenticate user and return JWT token."""
    from ..auth import create_access_token, pwd_context

    row = query_one(
        "SELECT id, username, hashed_password, is_active, is_admin FROM auth_users WHERE username = %s",
        (req.username,),
    )
    if not row or not row.get("hashed_password"):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not pwd_context.verify(req.password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not row.get("is_active"):
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token(data={"sub": row["username"], "is_admin": bool(row.get("is_admin", False))})
    return {"token": token}


class GCPRegisterRequest(BaseModel):
    project_id: str
    key_file_content: Optional[str] = None


@router.post("/auth/gcp/register", dependencies=[Depends(require_auth)])
async def register_gcp(request: GCPRegisterRequest) -> dict[str, Any]:
    """Register GCP credentials."""
    config_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    config: dict[str, Any] = {"project_id": request.project_id}
    if request.key_file_content:
        config["key_file_base64"] = base64.b64encode(request.key_file_content.encode()).decode()

    insert_and_return(
        "INSERT INTO cloud_config (id, provider, name, credential_type, config, created_at, updated_at) "
        "VALUES (%s, 'gcp', %s, 'service_account', %s, %s, %s) RETURNING id",
        (config_id, f"GCP {request.project_id}", config, now, now),
    )
    return {"config_id": config_id, "project_id": request.project_id}


class AzureServiceAccountRegisterRequest(BaseModel):
    tenant_id: str
    client_id: str
    client_secret: Optional[str] = None
    subscription_id: Optional[str] = None


@router.post("/auth/azure/service-account", dependencies=[Depends(require_auth)])
async def register_azure_service_account(request: AzureServiceAccountRegisterRequest) -> dict[str, Any]:
    """Register Azure service principal credentials."""
    config_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    config: dict[str, Any] = {
        "tenant_id": request.tenant_id,
        "client_id": request.client_id,
        "auth_method": "service_account",
    }
    if request.client_secret:
        config["client_secret"] = request.client_secret
    if request.subscription_id:
        config["subscription_id"] = request.subscription_id

    name = f"Azure SP ({request.tenant_id[:8]}...)" if len(request.tenant_id) > 8 else f"Azure SP ({request.tenant_id})"
    insert_and_return(
        "INSERT INTO cloud_config (id, provider, name, credential_type, config, created_at, updated_at) "
        "VALUES (%s, 'azure', %s, 'service_account', %s, %s, %s) RETURNING id",
        (config_id, name, config, now, now),
    )
    return {"config_id": config_id, "message": "Azure service account registered successfully"}


@router.post("/auth/login")
async def login_alias(req: TokenRequest) -> dict[str, Any]:
    """CLI-compatible login endpoint alias."""
    result = await login_token(req)
    return {"access_token": result["token"], "token_type": "bearer"}
