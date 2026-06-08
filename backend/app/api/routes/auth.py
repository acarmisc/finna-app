"""Auth endpoints — login and cloud credential registration."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from utils.encryption import encrypt_config

from .. import auth as api_auth
from ..db import execute, insert_and_return, query_one
from ..rate_limit import AUTH_LIMIT, limiter

require_auth = api_auth.require_auth
logger = logging.getLogger("api.auth")

router = APIRouter()


class TokenRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/token")
@limiter.limit(AUTH_LIMIT)
async def login_token(request: Request, req: TokenRequest) -> dict[str, Any]:
    """Authenticate user and return JWT token."""
    from ..auth import create_access_token, verify_password

    row = query_one(
        "SELECT id, username, hashed_password, is_active, is_admin FROM auth_users WHERE username = %s",
        (req.username,),
    )
    if not row or not row.get("hashed_password"):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(req.password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not row.get("is_active"):
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token(data={"sub": row["username"], "is_admin": bool(row.get("is_admin", False))})
    return {"token": token}


@router.get("/auth/github")
async def github_redirect() -> dict[str, Any]:
    """Return GitHub OAuth redirect URL."""
    from ..auth import get_github_redirect_url
    url = get_github_redirect_url()
    if not url:
        return {"error": "GitHub OAuth not configured", "url": None}
    return {"url": url}


class GitHubCallbackRequest(BaseModel):
    code: str


@router.post("/auth/github/callback")
@limiter.limit(AUTH_LIMIT)
async def github_callback(request: Request, req: GitHubCallbackRequest) -> dict[str, Any]:
    """Exchange GitHub code for JWT token."""
    from ..auth import (
        GITHUB_CLIENT_ID,
        create_access_token,
        exchange_github_code,
        get_github_user,
        get_github_user_emails,
    )

    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=503, detail="GitHub OAuth not configured")

    token_data = await exchange_github_code(req.code)
    if not token_data or "access_token" not in token_data:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token")

    access_token = token_data["access_token"]
    github_user = await get_github_user(access_token)
    if not github_user:
        raise HTTPException(status_code=400, detail="Failed to get GitHub user")

    github_id = str(github_user.get("id", ""))
    username = github_user.get("login", "")
    email = github_user.get("email")

    if not email:
        emails = await get_github_user_emails(access_token)
        for e in emails:
            if e.get("primary"):
                email = e.get("email")
                break

    if not email:
        raise HTTPException(status_code=400, detail="No email found in GitHub account")

    row = query_one("SELECT id, username, is_active, is_admin FROM auth_users WHERE github_id = %s", (github_id,))

    if not row:
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        execute(
            "INSERT INTO auth_users (id, username, email, github_id, is_active, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (user_id, username, email, github_id, True, now, now),
        )
        row = {"id": user_id, "username": username, "is_active": True, "is_admin": False}

    if not row.get("is_active"):
        raise HTTPException(status_code=403, detail="Account is disabled")

    jwt_token = create_access_token(data={"sub": row["username"], "is_admin": bool(row.get("is_admin", False))})
    return {"token": jwt_token}


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
        config = encrypt_config({"project_id": request.project_id, "key_file_content": request.key_file_content})

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
@limiter.limit(AUTH_LIMIT)
async def login_alias(request: Request, req: TokenRequest) -> dict[str, Any]:
    """CLI-compatible login endpoint alias."""
    result = await login_token(request, req)
    return {"access_token": result["token"], "token_type": "bearer"}
