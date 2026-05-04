"""Domain-specific query modules for FinOps API."""

from .alert_queries import (
    query_all_alerts,
    query_one_alert,
)
from .auth_queries import (
    insert_user_and_return,
    query_one_user,
)
from .base import (
    execute,
    insert_and_return,
    query_all,
    query_one,
)
from .config_queries import (
    execute_config,
    insert_config_and_return,
    query_all_configs,
    query_one_config,
)
from .cost_queries import (
    query_all_costs,
    query_one_cost,
)
from .extractor_queries import (
    execute_extractor,
    insert_extractor_and_return,
    query_all_extractors,
    query_one_extractor,
)

__all__ = [
    "query_all",
    "query_one",
    "execute",
    "insert_and_return",
    "query_all_costs",
    "query_one_cost",
    "query_all_configs",
    "query_one_config",
    "execute_config",
    "insert_config_and_return",
    "query_all_alerts",
    "query_one_alert",
    "query_one_user",
    "insert_user_and_return",
    "query_all_extractors",
    "query_one_extractor",
    "execute_extractor",
    "insert_extractor_and_return",
]
