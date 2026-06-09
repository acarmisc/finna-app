"""OIDC device authorization routes — RFC 8628 device code flow for CLI login."""

from __future__ import annotations

import logging
import time
from threading import Lock
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from utils.encryption import decrypt_config

from .. import auth as api_auth
from .. import oidc
from ..db import execute, insert_and_return, query_one
from ..models import (
    OIDCDevicePollRequest,
    OIDCDevicePollResponse,
    OIDCDeviceStartRequest,
    OIDCDeviceStartResponse,
)

logger = logging.getLogger("api.oidc_device_auth")

router = APIRouter()

# Per-IP rate limiting (same pattern as oidc_auth.py)
_lock = Lock()
_start_attempts: dict[str, list[float]] = {}
_poll_attempts: dict[str, list[float]] = {}


def _get_client_ip(request: Request) -> str:
    """Resolve client IP respecting reverse-proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(ip: str, store: dict[str, list[float]], max_attempts: int, window: int) -> bool:
    """Check if ip has exceeded rate limit. Returns True if rate limited."""
    now = time.monotonic()
    with _lock:
        if ip not in store:
            store[ip] = []
        store[ip] = [t for t in store[ip] if now - t < window]
        if len(store[ip]) >= max_attempts:
            return True
        store[ip].append(now)
    return False


def _apply_claim_mappings(claims: dict[str, Any], mappings: dict[str, Any]) -> dict[str, Any]:
    """Apply claim mappings to extract username, email, is_admin from token claims."""
    result: dict[str, Any] = {}

    # Username claim mapping
    username_claim = mappings.get("username", "preferred_username")
    result["username"] = claims.get(username_claim, "")

    # Email claim mapping
    email_claim = mappings.get("email", "email")
    result["email"] = claims.get(email_claim, "")

    # Admin rule: check if claim matches value
    result["is_admin"] = False
    admin_rule = mappings.get("is_admin", {})
    if isinstance(admin_rule, dict):
        rule_claim = admin_rule.get("claim")
        rule_match = admin_rule.get("match")
        if rule_claim and rule_match:
            claim_value = claims.get(rule_claim)
            if isinstance(claim_value, list):
                result["is_admin"] = rule_match in claim_value
            elif isinstance(claim_value, str):
                result["is_admin"] = claim_value == rule_match

    return result


@router.post("/auth/oidc/device")
async def oidc_device_start(
    req: OIDCDeviceStartRequest,
    request: Request,
) -> OIDCDeviceStartResponse:
    """Initiate OIDC device authorization flow for CLI login (RFC 8628).

    Returns a device code, user code, and verification URL. The CLI displays
    the URL and code, then polls POST /auth/oidc/device/callback until the
    user completes authentication in their browser.
    """
    ip = _get_client_ip(request)
    if _check_rate_limit(ip, _start_attempts, 5, 60):
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    # Get provider
    provider = query_one(
        "SELECT id, config FROM auth_providers WHERE id = %s AND enabled = true AND kind = 'oidc'",
        (req.provider_id,),
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found or disabled")

    config = decrypt_config(provider["config"])
    client_id = config.get("client_id", "")
    client_secret = config.get("client_secret", "")
    issuer = config.get("issuer", "")

    if not client_id:
        raise HTTPException(status_code=400, detail="Provider missing client_id")

    try:
        # Discover metadata (cached)
        metadata = await oidc.discover_provider(issuer)

        # Check if device flow is supported
        if not metadata.get("device_authorization_endpoint"):
            raise HTTPException(
                status_code=400,
                detail="Provider does not support device authorization flow",
            )

        # Request device code from provider
        device_data = await oidc.request_device_code(
            metadata,
            client_id=client_id,
            scopes=config.get("scopes", ["openid", "profile", "email"]),
        )

        device_code = device_data["device_code"]
        user_code = device_data["user_code"]
        verification_uri = device_data["verification_uri"]
        verification_uri_complete = device_data.get("verification_uri_complete")
        expires_in = device_data.get("expires_in", 600)
        interval = device_data.get("interval", 5)

        # Store device code metadata for later token exchange
        oidc.store_device_code(
            device_code=device_code,
            provider_id=str(provider["id"]),
            client_id=client_id,
            client_secret=client_secret,
            interval=interval,
            expires_in=expires_in,
        )

        return OIDCDeviceStartResponse(
            device_code=device_code,
            user_code=user_code,
            verification_uri=verification_uri,
            verification_uri_complete=verification_uri_complete,
            expires_in=expires_in,
            interval=interval,
        )

    except oidc.OIDCError as e:
        logger.error(f"OIDC device auth start error: {e}")
        raise HTTPException(status_code=400, detail=f"Login setup failed: {str(e)}") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during device auth start: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/auth/oidc/device/callback")
async def oidc_device_callback(
    req: OIDCDevicePollRequest,
    request: Request,
) -> OIDCDevicePollResponse:
    """Poll/exchange a device code for tokens.

    The CLI should call this endpoint repeatedly (respecting the interval from
    the start response) until status is "completed", "expired", or "denied".
    """
    ip = _get_client_ip(request)
    if _check_rate_limit(ip, _poll_attempts, 30, 60):
        raise HTTPException(status_code=429, detail="Too many polling attempts.")

    # Retrieve stored device code metadata
    stored = oidc.get_and_consume_device_code(req.device_code)
    if not stored:
        raise HTTPException(status_code=404, detail="Invalid or expired device code")

    provider_id = stored["provider_id"]
    client_id = stored["client_id"]
    client_secret = stored["client_secret"]

    # Get provider
    provider = query_one(
        "SELECT id, config FROM auth_providers WHERE id = %s AND enabled = true AND kind = 'oidc'",
        (provider_id,),
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found or disabled")

    config = decrypt_config(provider["config"])
    issuer = config.get("issuer", "")

    try:
        # Discover metadata (cached)
        metadata = await oidc.discover_provider(issuer)

        # Exchange device code for tokens
        token_data = await oidc.exchange_device_code(
            metadata,
            client_id=client_id,
            client_secret=client_secret,
            device_code=req.device_code,
            interval=stored.get("interval", 5),
        )

        # Handle error responses from the provider
        if "error" in token_data:
            error = token_data["error"]
            # Re-store if still pending (so the CLI can poll again)
            if error == "authorization_pending":
                oidc.store_device_code(
                    device_code=req.device_code,
                    provider_id=provider_id,
                    client_id=client_id,
                    client_secret=client_secret,
                    interval=stored.get("interval", 5),
                    expires_in=int(token_data.get("expires_in", 300)),
                )
                return OIDCDevicePollResponse(status="pending")
            elif error == "slow_down":
                oidc.store_device_code(
                    device_code=req.device_code,
                    provider_id=provider_id,
                    client_id=client_id,
                    client_secret=client_secret,
                    interval=stored.get("interval", 5),
                    expires_in=int(token_data.get("expires_in", 300)),
                )
                return OIDCDevicePollResponse(status="pending")
            elif error in ("expired_token", "access_denied"):
                return OIDCDevicePollResponse(status="expired" if error == "expired_token" else "denied")
            else:
                raise oidc.OIDCError(f"Provider error: {error}")

        # Success — extract tokens
        id_token = token_data.get("id_token", "")
        if not id_token:
            raise oidc.OIDCError("No id_token in device code token response")

        # We don't have a nonce from device code flow (RFC 8628 §11),
        # so use a sentinel. The nonce check in verify_id_token is not
        # strictly required for device flow since the code is the secret.
        # We verify without nonce binding.
        claims = await oidc.verify_id_token_no_nonce(id_token, metadata, client_id)

        # Apply claim mappings
        mappings = config.get("claim_mappings", {})
        mapped = _apply_claim_mappings(claims, mappings)

        username = mapped.get("username", "")
        email = mapped.get("email", "")
        is_admin = mapped.get("is_admin", False)

        if not username or not email:
            raise HTTPException(status_code=400, detail="Missing required claims (username, email)")

        # Email domain filter
        allowed_domains = config.get("allowed_email_domains", [])
        if allowed_domains:
            email_domain = email.split("@")[1] if "@" in email else ""
            if email_domain not in allowed_domains:
                raise HTTPException(status_code=403, detail="Email domain not allowed")

        # Look up user by (provider_id, oidc_subject)
        oidc_subject = claims.get("sub", "")
        user = query_one(
            "SELECT id, username, is_admin FROM auth_users WHERE oidc_provider_id = %s AND oidc_subject = %s",
            (provider_id, oidc_subject),
        )

        if not user:
            # Auto-provision if enabled
            if not config.get("auto_provision", False):
                raise HTTPException(status_code=403, detail="User not provisioned. Contact admin.")

            # Create new user
            db_id = insert_and_return(
                """
                INSERT INTO auth_users
                    (username, email, oidc_provider_id, oidc_subject, oidc_claims, is_admin, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, true)
                RETURNING id
                """,
                (username, email, provider_id, oidc_subject, claims, is_admin),
            )
            user = {"id": int(db_id), "username": username, "is_admin": is_admin}
        else:
            # Update is_admin based on current claim mapping
            execute(
                "UPDATE auth_users SET is_admin = %s, oidc_claims = %s WHERE id = %s",
                (is_admin, claims, user["id"]),
            )
            user["is_admin"] = is_admin

        # Issue Finna JWT
        token = api_auth.create_access_token(
            {"sub": user["username"], "is_admin": user.get("is_admin", False)}
        )

        return OIDCDevicePollResponse(
            status="completed",
            token=token,
            user_id=user["id"],
            username=user["username"],
        )

    except oidc.OIDCError as e:
        logger.error(f"OIDC device code exchange error: {e}")
        # Re-store so CLI can retry
        oidc.store_device_code(
            device_code=req.device_code,
            provider_id=provider_id,
            client_id=client_id,
            client_secret=client_secret,
            interval=stored.get("interval", 5),
            expires_in=300,
        )
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during device code exchange: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e
