"""Pydantic v2 configuration models for the aggregation engine.

Supports per-metric-type settings (window size, retention days) and
loading from YAML configuration files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Per-metric-type settings
# ---------------------------------------------------------------------------


class MetricAggregationSettings(BaseModel):
    """Aggregation settings for a single metric type."""

    window_size_minutes: int = Field(
        gt=0,
        description="Aggregation window size in minutes.",
    )
    retention_days: int = Field(
        gt=0,
        description="How long to retain aggregated data, in days.",
    )


class AggregationConfig(BaseModel):
    """Top-level aggregation configuration containing per-metric-type settings.

    Default values:
        - infra_metrics: 15m window / 365d retention
        - llm_requests:  5m window / 180d retention
        - billing:       60m (1h) window / 730d retention
    """

    infra_metrics: MetricAggregationSettings = Field(
        default_factory=lambda: MetricAggregationSettings(
            window_size_minutes=15,
            retention_days=365,
        ),
    )
    llm_requests: MetricAggregationSettings = Field(
        default_factory=lambda: MetricAggregationSettings(
            window_size_minutes=5,
            retention_days=180,
        ),
    )
    billing: MetricAggregationSettings = Field(
        default_factory=lambda: MetricAggregationSettings(
            window_size_minutes=60,
            retention_days=730,
        ),
    )

    # Allow additional metric types not known at schema time
    model_config = {"extra": "allow"}

    def get_settings(self, metric_type: str) -> MetricAggregationSettings:
        """Return aggregation settings for a given metric type.

        Falls back to infra_metrics defaults if the metric type is not
        explicitly configured.
        """
        value = getattr(self, metric_type, None)
        if value is not None and isinstance(value, MetricAggregationSettings):
            return value
        return self.infra_metrics


# ---------------------------------------------------------------------------
# Client-scoped config
# ---------------------------------------------------------------------------


class ClientConfig(BaseModel):
    """Configuration wrapper for a specific client, aggregating settings."""

    client_id: str = Field(description="Unique client identifier.")
    client_name: Optional[str] = Field(default=None, description="Human-readable client name.")
    aggregation: AggregationConfig = Field(
        default_factory=AggregationConfig,
        description="Aggregation settings for this client.",
    )


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


def load_aggregation_config(path: str | Path) -> AggregationConfig:
    """Load an AggregationConfig from a YAML file.

    The YAML file should have a top-level ``aggregation`` key, or the
    entire file is treated as the aggregation config if no such key exists.

    Example YAML::

        aggregation:
          infra_metrics:
            window_size_minutes: 15
            retention_days: 365
          llm_requests:
            window_size_minutes: 5
            retention_days: 180
          billing:
            window_size_minutes: 60
            retention_days: 730
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Aggregation config file not found: {path}")

    with path.open() as f:
        data = yaml.safe_load(f)

    if data is None:
        return AggregationConfig()

    # If there's an 'aggregation' key, unwrap it
    agg_data = data.get("aggregation", data)

    # Convert nested dicts to MetricAggregationSettings where appropriate
    known_keys = {"infra_metrics", "llm_requests", "billing"}
    for key in known_keys:
        if key in agg_data and isinstance(agg_data[key], dict):
            agg_data[key] = MetricAggregationSettings(**agg_data[key])

    # Handle any extra metric types the user may have defined
    for key, value in agg_data.items():
        if key not in known_keys and isinstance(value, dict):
            agg_data[key] = MetricAggregationSettings(**value)

    return AggregationConfig(**agg_data)


def load_client_config(path: str | Path) -> ClientConfig:
    """Load a ClientConfig from a YAML file.

    The YAML should have ``client_id`` and an ``aggregation`` section.

    Example YAML::

        client_id: acme-corp
        client_name: Acme Corporation
        aggregation:
          infra_metrics:
            window_size_minutes: 15
            retention_days: 365
          llm_requests:
            window_size_minutes: 5
            retention_days: 180
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Client config file not found: {path}")

    with path.open() as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"Empty config file: {path}")

    agg_data = data.pop("aggregation", {})

    known_keys = {"infra_metrics", "llm_requests", "billing"}
    for key in known_keys:
        if key in agg_data and isinstance(agg_data[key], dict):
            agg_data[key] = MetricAggregationSettings(**agg_data[key])

    for key, value in agg_data.items():
        if key not in known_keys and isinstance(value, dict):
            agg_data[key] = MetricAggregationSettings(**value)

    return ClientConfig(
        client_id=data["client_id"],
        client_name=data.get("client_name"),
        aggregation=AggregationConfig(**agg_data),
    )
