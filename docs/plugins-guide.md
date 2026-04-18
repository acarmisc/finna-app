# Extractor Plugin Guide

Finna uses a plugin-based architecture for data extraction. This allows internal and external contributors to add new cloud providers or data sources without modifying the core orchestrator logic.

## Core Concepts

An **Extractor Plugin** is a Python class that:
1.  Inherits from `extractors.base.ExtractorPlugin`.
2.  Is decorated with `@extractor_plugin`.
3.  Implements the `extract()` method.
4.  Declares its configuration requirements via `config_fields()`.

## Directory Structure

Plugins reside in the `extractors/` directory. While built-in plugins (like `gcp_billing`) are registered in `extractors/plugins.py`, you can create a standalone file for your custom plugin.

## Implementation Example

```python
from extractors.base import ExtractorPlugin, ConfigField, extractor_plugin

@extractor_plugin(
    "my_custom_source",
    display_name="My Custom API",
    description="Extracts data from an internal cost API"
)
class MyCustomPlugin(ExtractorPlugin):
    def extract(self) -> int:
        # 1. Read configuration (passed from cloud_config JSON in DB)
        api_key = self.config.get("api_key")
        
        # 2. Perform extraction logic
        # data = fetch_from_api(api_key)
        
        # 3. Write to PostgreSQL using self.pg_dsn
        # insert_records(self.pg_dsn, data)
        
        return 100  # Return number of records inserted

    def health_name(self) -> str:
        return "my_custom_source"

    @classmethod
    def config_fields(cls) -> list[ConfigField]:
        """
        Define fields the frontend should render in the 
        'New Connection' modal for this provider.
        """
        return [
            ConfigField(
                name="api_key", 
                label="API Key", 
                field_type="password", 
                placeholder="sk-..."
            ),
            ConfigField(
                name="endpoint", 
                label="Custom Endpoint", 
                required=False,
                default="https://api.internal.co"
            )
        ]

    @classmethod
    def auth_methods(cls) -> list[dict[str, str]]:
        """
        Define supported authentication methods.
        """
        return [
            {"id": "apikey", "label": "API Key", "sub": "Static token authentication"}
        ]
```

## Discovery

The API automatically discovers plugins in two ways:
1.  **Built-in**: Any module listed in `extractors.plugins.DISCOVERY_MODULES`.
2.  **Environment Variable**: Modules listed in `EXTRACTOR_PLUGINS` (comma-separated).

Example for local dev:
```bash
export EXTRACTOR_PLUGINS="extractors.my_custom_source"
```

## Frontend Integration

When you register a plugin, the frontend `NewConnectionModal` dynamically queries the `/api/v1/plugins` endpoint. 
It will:
-   Show your plugin in the Provider dropdown.
-   Render the exact form fields you defined in `config_fields()`.
-   Handle validation based on the `required` flag.

## Testing Your Plugin

You can test your plugin standalone by invoking its `extract()` method in a script, or by using the `EXTRACTOR_TYPE` env var with the docker-compose setup:

```bash
EXTRACTOR_TYPE=my_custom_source docker compose --profile extractors up extractor
```
