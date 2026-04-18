"""Extractor plugin base class and registry.

Every extractor is a plugin that subclasses ExtractorPlugin and registers
itself via the @extractor_plugin decorator. The registry discovers plugins
at startup, provides metadata to the API, and routes run requests.

To write a new extractor:
  1. Create a file in extractors/ (e.g. extractors/my_source.py)
  2. Subclass ExtractorPlugin
  3. Decorate with @extractor_plugin("my_source")
  4. Implement extract(), health_name(), display_name(), config_fields()
  5. Add "my_source" to EXTRACTOR_TYPE env or call POST /api/v1/plugins/my_source/run
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Global plugin registry: extractor_type -> ExtractorPlugin subclass
_REGISTRY: dict[str, type[ExtractorPlugin]] = {}


@dataclass
class ConfigField:
    """Describes a single configuration field for a plugin."""

    name: str
    label: str
    field_type: str = "text"  # text | password | select | checkbox
    required: bool = True
    default: Any = None
    placeholder: str = ""
    options: list[dict[str, str]] = field(default_factory=list)  # for select type: [{value, label}]


class ExtractorPlugin(ABC):
    """Base class for all Finna extractor plugins.

    Subclass this and decorate with @extractor_plugin("type_key") to
    register a new extractor. The type_key must be unique across all plugins.

    Lifecycle:
      1. Plugin is discovered and registered at import time
      2. API calls GET /plugins → returns metadata from all registered plugins
      3. API calls POST /plugins/{type}/run → instantiates the plugin and calls extract()
      4. Plugin reads config from env vars (set by the runner from cloud_config)
      5. Plugin writes rows to PostgreSQL via self.pg_dsn
    """

    # Set by @extractor_plugin decorator
    extractor_type: str = ""
    display_name: str = ""
    description: str = ""

    @abstractmethod
    def extract(self) -> int:
        """Run extraction and return the number of records inserted.

        Config is available via self.config (populated from cloud_config
        JSON), env vars, or explicit kwargs.

        Returns:
            Number of records extracted and inserted.
        """

    @abstractmethod
    def health_name(self) -> str:
        """Identifier written to extractor_health table (e.g. 'gcp_billing')."""

    @classmethod
    def config_fields(cls) -> list[ConfigField]:
        """Return the list of config fields this plugin requires.

        Override this to declare what fields the frontend should render
        in the connection creation wizard.
        """
        return []

    @classmethod
    def auth_methods(cls) -> list[dict[str, str]]:
        """Return supported auth methods for this plugin.

        Each dict: {id: str, label: str, sub: str}
        """
        return []

    @classmethod
    def provider_id(cls) -> str:
        """The provider identifier (e.g. 'azure', 'gcp', 'llm')."""
        return cls.extractor_type.split("_")[0] if "_" in cls.extractor_type else cls.extractor_type

    def __init__(self, config: dict[str, Any] | None = None, pg_dsn: str = ""):
        self.config = config or {}
        self.pg_dsn = pg_dsn or os.getenv("PG_DSN", "")

    @classmethod
    def to_metadata(cls) -> dict[str, Any]:
        """Serialize plugin metadata for the /plugins API endpoint."""
        return {
            "type": cls.extractor_type,
            "provider": cls.provider_id(),
            "display_name": cls.display_name,
            "description": cls.description,
            "auth_methods": cls.auth_methods(),
            "config_fields": [
                {
                    "name": f.name,
                    "label": f.label,
                    "type": f.field_type,
                    "required": f.required,
                    "default": f.default,
                    "placeholder": f.placeholder,
                    "options": f.options,
                }
                for f in cls.config_fields()
            ],
        }


def extractor_plugin(extractor_type: str, display_name: str = "", description: str = ""):
    """Decorator to register an ExtractorPlugin subclass.

    Usage:
        @extractor_plugin("gcp_billing", display_name="GCP Billing", description="...")
        class GCPBillingExtractor(ExtractorPlugin):
            ...
    """

    def decorator(cls: type[ExtractorPlugin]) -> type[ExtractorPlugin]:
        cls.extractor_type = extractor_type
        cls.display_name = display_name or extractor_type
        cls.description = description
        if extractor_type in _REGISTRY:
            logger.warning(f"Overwriting existing plugin: {extractor_type}")
        _REGISTRY[extractor_type] = cls
        return cls

    return decorator


def get_plugin(extractor_type: str) -> type[ExtractorPlugin] | None:
    """Look up a registered plugin by extractor type."""
    return _REGISTRY.get(extractor_type)


def list_plugins() -> dict[str, type[ExtractorPlugin]]:
    """Return all registered plugins."""
    return dict(_REGISTRY)


def plugin_metadata() -> list[dict[str, Any]]:
    """Return metadata for all registered plugins."""
    return [cls.to_metadata() for cls in _REGISTRY.values()]
