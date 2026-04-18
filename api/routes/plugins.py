"""Plugin discovery and management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth import require_auth
from extractors.plugins import list_plugins

router = APIRouter()


@router.get("/plugins", dependencies=[Depends(require_auth)])
async def get_plugins() -> list[dict]:
    """Return metadata for all registered extractor plugins.

    This endpoint enables the frontend to dynamically render connection
    creation forms based on each plugin's declared config_fields and
    auth_methods. Third-party plugins discovered via EXTRACTOR_PLUGINS
    env var are included automatically.
    """
    from extractors.base import plugin_metadata

    return plugin_metadata()


@router.get("/plugins/{extractor_type}", dependencies=[Depends(require_auth)])
async def get_plugin_detail(extractor_type: str) -> dict:
    """Return metadata for a single plugin."""
    from extractors.base import get_plugin

    cls = get_plugin(extractor_type)
    if not cls:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Plugin '{extractor_type}' not found")
    return cls.to_metadata()
