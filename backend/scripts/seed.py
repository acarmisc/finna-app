"""Seed script to load sample data into the database."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("seed")


def get_pg_dsn() -> str:
    dsn = os.getenv("PG_DSN")
    if not dsn:
        # Try a sensible default for local dev
        dsn = "postgresql://postgres:postgres@localhost:5432/finops"
        logger.warning(f"PG_DSN not set, using default: {dsn}")
    return dsn


def load_fixtures() -> dict[str, list[dict[str, Any]]]:
    fixture_path = Path(__file__).parent.parent.parent / "resources" / "fixtures" / "sample_data.json"
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture file not found: {fixture_path}")

    with open(fixture_path, "r") as f:
        return json.load(f)


def seed():
    dsn = get_pg_dsn()
    fixtures = load_fixtures()

    try:
        with psycopg.connect(dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                logger.info("Cleaning up existing data...")
                # Order matters due to foreign keys
                cur.execute("DELETE FROM extractor_runs")
                cur.execute("DELETE FROM cloud_config")
                # cost_records might be large or partitioned, use TRUNCATE if possible
                cur.execute("TRUNCATE TABLE cost_records CASCADE")

                logger.info("Seeding cloud_config...")
                for item in fixtures.get("cloud_config", []):
                    cur.execute(
                        """
                        INSERT INTO cloud_config (id, provider, name, credential_type, config)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            item["id"],
                            item["provider"],
                            item["name"],
                            item["credential_type"],
                            json.dumps(item["config"]),
                        ),
                    )

                logger.info("Seeding extractor_runs...")
                for item in fixtures.get("extractor_runs", []):
                    cur.execute(
                        """
                        INSERT INTO extractor_runs (config_id, provider, extractor_type, status, records_extracted, started_at, finished_at, error_message)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            item["config_id"],
                            item["provider"],
                            item["extractor_type"],
                            item["status"],
                            item.get("records_extracted", 0),
                            item["started_at"],
                            item.get("finished_at"),
                            item.get("error_message"),
                        ),
                    )

                logger.info("Seeding cost_records...")
                for item in fixtures.get("cost_records", []):
                    cur.execute(
                        """
                        INSERT INTO cost_records (
                            record_id, provider, usage_start, usage_end, account_id, project_id,
                            service_category, service_name, resource_id, cost_usd, 
                            currency_original, cost_original, net_cost_usd, tags,
                            model_name, total_tokens
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            item["record_id"],
                            item["provider"],
                            item["usage_start"],
                            item["usage_end"],
                            item["account_id"],
                            item["project_id"],
                            item["service_category"],
                            item["service_name"],
                            item.get("resource_id"),
                            item["cost_usd"],
                            item["currency_original"],
                            item["cost_original"],
                            item["net_cost_usd"],
                            json.dumps(item.get("tags", {})),
                            item.get("model_name"),
                            item.get("total_tokens"),
                        ),
                    )

                # Refresh daily_costs materialized view
                logger.info("Refreshing daily_costs materialized view...")
                cur.execute("REFRESH MATERIALIZED VIEW daily_costs")

            conn.commit()
            logger.info("Seeding completed successfully!")

    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        raise


if __name__ == "__main__":
    seed()
