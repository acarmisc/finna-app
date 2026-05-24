"""OIDC authentication routes — login, callback, provider listing, testing."""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from utils.encryption import decrypt_config

from .. import auth as api_auth
from .. import oidc
from ..db import execute, insert_and_return, query_all, query_one

require_auth = api_auth.require_auth
require_admin = api_auth.require_admin
logger = logging.getLogger("api.oidc_auth")

router = APIRouter()

# Rate limiting: IP -> (attempt_count, window_start_time)
_login_attempts: dict[str, tuple[int, float]] = {}
_callback_attempts: dict[str, tuple[int, float]] = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 10  # max attempts per window


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    if request.client:
        return request.client.host
    return "unknown"


def _check_rate_limit(attempts_dict: dict[str, tuple[int, float]], ip: str, max_attempts: int = RATE_LIMIT_MAX) -> bool:
    """Check rate limit for IP. Returns True if allowed, False if rate-limited."""
    now = time.time()
    if ip in attempts_dict:
        count, window_start = attempts_dict[ip]
        # Reset if window expired
        if now - window_start > RATE_LIMIT_WINDOW:
            attempts_dict[ip] = (1, now)
            return True
        # Check limit
        if count >= max_attempts:
            return False
        # Increment
        attempts_dict[ip] = (count + 1, window_start)
        return True
    else:
        # First attempt in window
        attempts_dict[ip] = (1, now)
        return True


def _apply_claim_mappings(claims: dict[str, Any], mappings: dict[str, Any]) -> dict[str, Any]:
    """Apply claim mappings to extract username, email, is_admin from token claims."""
    result = {}

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
                # For array claims like groups
                result["is_admin"] = rule_match in claim_value
            elif isinstance(claim_value, str):
                result["is_admin"] = claim_value == rule_match

    return result


class OIDCLoginRequest(BaseModel):
    """Login request."""
    provider_id: str


class OIDCLoginResponse(BaseModel):
    """Login response."""
    authorization_url: str
    state: str


class OIDCCallbackRequest(BaseModel):
    """Callback request."""
    provider_id: str
    code: str
    state: str


class OIDCCallbackResponse(BaseModel):
    """Callback response."""
    token: str
    user_id: int
    username: str


class ProviderPublic(BaseModel):
    """Public provider info (no secrets)."""
    id: str
    name: str
    issuer: str
    enabled: bool


@router.get("/auth/oidc/providers")
async def list_enabled_providers() -> list[ProviderPublic]:
    """List enabled OIDC providers (public, no auth required)."""
    rows = query_all(
        """
        SELECT id, name, config, enabled
        FROM auth_providers
        WHERE enabled = true AND kind = 'oidc'
        ORDER BY name
        """
    )

    providers = []
    for row in rows:
        config = decrypt_config(row["config"])
        providers.append(
            ProviderPublic(
                id=row["id"],
                name=row["name"],
                issuer=config.get("issuer", ""),
                enabled=row["enabled"],
            )
        )
    return providers


@router.post("/auth/oidc/login")
async def oidc_login(request_data: OIDCLoginRequest, request: Request) -> OIDCLoginResponse:
    """Initiate OIDC login — return authorization URL with PKCE."""
    ip = _get_client_ip(request)

    # Rate limit
    if not _check_rate_limit(_login_attempts, ip):
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    # Get provider
    provider = query_one(
        "SELECT id, config FROM auth_providers WHERE id = %s AND enabled = true AND kind = 'oidc'",
        (request_data.provider_id,),
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found or disabled")

    config = decrypt_config(provider["config"])

    try:
        # Discover metadata
        issuer = config.get("issuer", "")
        metadata = await oidc.discover_provider(issuer)

        # Generate PKCE
        code_verifier, code_challenge = oidc.generate_pkce_pair()

        # Generate state and nonce
        state, nonce = oidc.generate_state_and_nonce()

        # Store state (for callback validation)
        oidc.store_state(state, UUID(provider["id"]), nonce, code_verifier)

        # Build authorization URL
        auth_url = oidc.build_authorization_url(
            metadata,
            client_id=config.get("client_id", ""),
            redirect_uri=config.get("redirect_uri", ""),
            state=state,
            nonce=nonce,
            code_challenge=code_challenge,
            scopes=config.get("scopes", ["openid", "profile", "email"]),
        )

        return OIDCLoginResponse(authorization_url=auth_url, state=state)

    except oidc.OIDCError as e:
        logger.error(f"OIDC login error: {e}")
        raise HTTPException(status_code=400, detail=f"Login setup failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/auth/oidc/callback")
async def oidc_callback(req: OIDCCallbackRequest, request: Request) -> OIDCCallbackResponse:
    """Handle OIDC callback — exchange code for token and provision user."""
    ip = _get_client_ip(request)

    # Rate limit
    if not _check_rate_limit(_callback_attempts, ip):
        raise HTTPException(status_code=429, detail="Too many callback attempts. Try again later.")

    # Get provider
    provider = query_one(
        "SELECT id, config FROM auth_providers WHERE id = %s AND enabled = true AND kind = 'oidc'",
        (req.provider_id,),
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found or disabled")

    config = decrypt_config(provider["config"])

    try:
        # Validate state and retrieve nonce, code_verifier
        provider_id, nonce, code_verifier = oidc.validate_and_consume_state(req.state)

        if provider_id != provider["id"]:
            raise oidc.OIDCError("State provider_id mismatch")

        # Discover metadata
        issuer = config.get("issuer", "")
        metadata = await oidc.discover_provider(issuer)

        # Exchange code for tokens
        tokens = await oidc.exchange_code(
            metadata,
            client_id=config.get("client_id", ""),
            client_secret=config.get("client_secret", ""),
            code=req.code,
            code_verifier=code_verifier,
            redirect_uri=config.get("redirect_uri", ""),
        )

        id_token = tokens.get("id_token", "")
        if not id_token:
            raise oidc.OIDCError("No id_token in token response")

        # Verify ID token
        claims = await oidc.verify_id_token(id_token, metadata, config.get("client_id", ""), nonce)

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
            (provider["id"], oidc_subject),
        )

        if not user:
            # Auto-provision if enabled
            if not config.get("auto_provision", False):
                raise HTTPException(status_code=403, detail="User not provisioned. Contact admin.")

            # Create new user
            import uuid
            user_id = str(uuid.uuid4())

            insert_and_return(
                """
                INSERT INTO auth_users (
                    id, username, email, oidc_provider_id,
                    oidc_subject, oidc_claims, is_admin, is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, true)
                RETURNING id
                """,
                (user_id, username, email, provider["id"], oidc_subject, claims, is_admin),
            )
            user = {"id": user_id, "username": username, "is_admin": is_admin}
        else:
            # Update is_admin based on current claim mapping (group changes propagate)
            execute(
                "UPDATE auth_users SET is_admin = %s, oidc_claims = %s WHERE id = %s",
                (is_admin, claims, user["id"]),
            )
            user["is_admin"] = is_admin

        # Issue Finna JWT
        token = api_auth.create_access_token(
            {"sub": user["username"], "is_admin": user.get("is_admin", False)}
        )

        return OIDCCallbackResponse(
            token=token,
            user_id=int(user["id"]) if isinstance(user["id"], str) and user["id"].isdigit() else user["id"],
            username=user["username"],
        )

    except oidc.OIDCError as e:
        logger.error(f"OIDC callback error: {e}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during callback: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/auth/oidc/logout", dependencies=[Depends(require_auth)])
async def oidc_logout(user: dict[str, Any] = Depends(require_auth)) -> dict[str, str]:
    """Best-effort logout with RP-initiated support."""
    # For v1: just return success. Token will expire on client.
    # RP-initiated logout URL returned if provider supports end_session_endpoint.
    return {"message": "Logged out"}


@router.post("/auth/oidc/test", dependencies=[Depends(require_admin)])
async def test_oidc_provider(request_data: OIDCLoginRequest) -> dict[str, Any]:
    """Test OIDC provider discovery and configuration."""
    provider = query_one(
        "SELECT id, name, config FROM auth_providers WHERE id = %s",
        (request_data.provider_id,),
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    config = decrypt_config(provider["config"])
    issuer = config.get("issuer", "")

    if not issuer:
        raise HTTPException(status_code=400, detail="Provider config missing issuer")

    try:
        metadata = await oidc.discover_provider(issuer)
        jwks = await oidc.get_jwks(issuer)

        return {
            "success": True,
            "provider_name": provider["name"],
            "issuer": issuer,
            "endpoints": {
                "authorization": metadata.get("authorization_endpoint"),
                "token": metadata.get("token_endpoint"),
                "userinfo": metadata.get("userinfo_endpoint"),
                "jwks": metadata.get("jwks_uri"),
                "end_session": metadata.get("end_session_endpoint"),
            },
            "jwks_keys_count": len(jwks.get("keys", [])),
        }

    except oidc.OIDCError as e:
        logger.error(f"OIDC test error: {e}")
        raise HTTPException(status_code=400, detail=f"Test failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error during test: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
