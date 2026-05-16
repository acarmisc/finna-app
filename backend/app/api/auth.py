"""JWT authentication module for API endpoints."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt  # type: ignore[import-untyped]

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable is required")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_CALLBACK_URL = os.getenv("GITHUB_CALLBACK_URL", "http://localhost:5173/#/auth/callback")

# Simple in-memory user storage (for demo purposes)
USERS_TABLE = {
    "admin": {
        "password_hash": "placeholder",
        "username": "admin",
        "email": "admin@finops.local"
    }
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET environment variable is not set")

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt  # type: ignore[no-any-return]


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token."""
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET environment variable is not set")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload  # type: ignore[no-any-return]
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


verify_token = decode_token


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """Dependency to get the current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        username: str = payload.get("sub")  # type: ignore[assignment]
        if username is None:
            raise credentials_exception
        return {"username": username, **payload}
    except HTTPException:
        raise credentials_exception
    except Exception:
        raise credentials_exception


def require_auth(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Require authentication dependency."""
    return user


async def require_admin(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Require admin role dependency."""
    is_admin = user.get("is_admin", False)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return user


async def token_verification_middleware(request: Request, call_next):
    """Middleware to verify JWT token on all protected routes."""
    if request.url.path.startswith("/api/v1/") and request.url.path != "/api/v1/auth/token":
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                decode_token(token)
            except HTTPException:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        else:
            if request.url.path != "/api/v1/healthz":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    return await call_next(request)


def get_github_redirect_url() -> str | None:
    """Generate GitHub OAuth redirect URL."""
    if not GITHUB_CLIENT_ID:
        return None
    import urllib.parse
    params = urllib.parse.urlencode({
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_CALLBACK_URL,
        "scope": "read:user email",
        "state": secrets.token_urlsafe(32),
    })
    return f"https://github.com/login/oauth/authorize?{params}"


async def exchange_github_code(code: str) -> dict[str, Any] | None:
    """Exchange GitHub code for access token."""
    import httpx
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        return None

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_CALLBACK_URL,
            },
            headers={"Accept": "application/json"},
        )
        if response.status_code != 200:
            return None
        data: dict[str, Any] = response.json()
        return data


async def get_github_user(access_token: str) -> dict[str, Any] | None:
    """Get GitHub user info using access token."""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {access_token}",
                "Accept": "application/json",
            },
        )
        if response.status_code != 200:
            return None
        data: dict[str, Any] = response.json()
        return data


async def get_github_user_emails(access_token: str) -> list[dict[str, Any]]:
    """Get GitHub user emails."""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user/emails",
            headers={
                "Authorization": f"token {access_token}",
                "Accept": "application/json",
            },
        )
        if response.status_code != 200:
            return []
        data: list[dict[str, Any]] = response.json()
        return data
