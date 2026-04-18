"""Auth endpoints for device code flow and credential registration."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.auth import require_auth
from backend.app.db import insert_and_return

logger = logging.getLogger("backend.app.auth")

router = APIRouter()

# In-memory store for pending device code flows
# Structure: {device_code: {"tenant_id": ..., "client_id": ..., "expires_at": ...}}
_device_codes: dict[str, dict[str, Any]] = {}


class DeviceCodeStartRequest(BaseModel):
    tenant_id: str = "organizations"
    client_id: Optional[str] = None


class DeviceCodeStartResponse(BaseModel):
    verification_uri: str
    user_code: str
    device_code: str
    expires_in: int = 900
    interval: int = 5
    message: str


class DeviceCodePollRequest(BaseModel):
    device_code: str
    tenant_id: str = "organizations"
    client_id: Optional[str] = None


class DeviceCodePollResponse(BaseModel):
    status: str  # "pending" | "completed" | "expired" | "failed"
    config_id: Optional[str] = None


AZURE_DEVICE_CODE_CLIENT = "04b07795-a71b-4e6a-8f4e-d9e78e1a5c0e"


@router.post("/auth/azure/device-code", response_model=DeviceCodeStartResponse, dependencies=[Depends(require_auth)])
async def start_device_code(request: DeviceCodeStartRequest) -> dict[str, Any]:
    """Start Azure device code flow."""
    from azure.identity import DeviceCodeCredential

    client_id = request.client_id or AZURE_DEVICE_CODE_CLIENT
    device_code = str(uuid.uuid4())

    # Store pending flow
    _device_codes[device_code] = {
        "tenant_id": request.tenant_id,
        "client_id": client_id,
        "started_at": datetime.now(timezone.utc),
    }

    try:
        # Create credential to initiate flow
        DeviceCodeCredential(
            client_id=client_id,
            tenant_id=request.tenant_id,
        )

        # The credential will raise if we try to get_token immediately
        # But we can get the flow info from MSAL
        from msal import Application

        app = Application(
            client_id=client_id,
            authority=f"https://login.microsoftonline.com/{request.tenant_id}",
        )

        flow = app.initiate_device_flow(scopes=["https://management.azure.com/.default"])

        verification_uri = flow.get("verification_uri", "https://microsoft.com/devicelogin")
        user_code = flow.get("user_code", "")

        return {
            "verification_uri": verification_uri,
            "user_code": user_code,
            "device_code": flow.get("device_code", ""),
            "expires_in": flow.get("expires_in", 900),
            "interval": flow.get("interval", 5),
            "message": flow.get("message", "Enter the code to authenticate"),
        }

    except Exception as e:
        logger.error(f"Failed to start device code flow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start device code flow: {e}")


@router.post(
    "/auth/azure/device-code/poll",
    response_model=DeviceCodePollResponse,
    dependencies=[Depends(require_auth)],
)
async def poll_device_code(request: DeviceCodePollRequest) -> dict[str, Any]:
    """Poll for device code completion."""
    from msal import Application

    device_code = request.device_code
    if device_code not in _device_codes:
        return {"status": "failed", "config_id": None}

    pending = _device_codes[device_code]
    tenant_id = request.tenant_id
    client_id = request.client_id or pending.get("client_id", AZURE_DEVICE_CODE_CLIENT)

    try:
        app = Application(
            client_id=client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
        )

        result = app.acquire_token_by_device_flow(
            scopes=["https://management.azure.com/.default"],
            device_code=device_code,
        )

        if "access_token" in result:
            # Success! Save config to DB
            token_result = result
            config_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            # Extract token for storage
            token_result.get("access_token")

            # For device code, we don't get client_secret
            # We store the token result differently
            config = {
                "tenant_id": tenant_id,
                "client_id": client_id,
                "auth_method": "device_code",
                "token_result": {k: v for k, v in token_result.items() if k != "access_token"},
            }

            sql = """
                INSERT INTO cloud_config (id, provider, name, credential_type, config, created_at, updated_at)
                VALUES (%s, 'azure', %s, 'device_code', %s, %s, %s)
                RETURNING id
            """
            insert_and_return(
                sql,
                (
                    config_id,
                    f"Azure Device Code ({now.strftime('%Y-%m-%d')})",
                    config,
                    now,
                    now,
                ),
            )

            # Clean up
            _device_codes.pop(device_code, None)

            return {"status": "completed", "config_id": config_id}

        elif "error" in result:
            error = result.get("error")
            if error in ("authorization_pending", "slow_down"):
                return {"status": "pending", "config_id": None}
            else:
                return {"status": "failed", "config_id": None}

        return {"status": "pending", "config_id": None}

    except Exception as e:
        logger.error(f"Device code poll error: {e}")
        return {"status": "pending", "config_id": None}


# GCP Register Endpoint
class GCPRegisterRequest(BaseModel):
    project_id: str
    key_file_content: Optional[str] = None


@router.post("/auth/gcp/register", dependencies=[Depends(require_auth)])
async def register_gcp(request: GCPRegisterRequest) -> dict[str, Any]:
    """Register GCP credentials."""
    import uuid

    config_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    config = {
        "project_id": request.project_id,
    }

    # If key file provided, encode it
    if request.key_file_content:
        import base64

        config["key_file_base64"] = base64.b64encode(request.key_file_content.encode()).decode()

    sql = """
        INSERT INTO cloud_config (id, provider, name, credential_type, config, created_at, updated_at)
        VALUES (%s, 'gcp', %s, 'service_account', %s, %s, %s)
        RETURNING id
    """
    insert_and_return(
        sql,
        (config_id, f"GCP {request.project_id}", config, now, now),
    )

    return {"config_id": config_id, "project_id": request.project_id}
