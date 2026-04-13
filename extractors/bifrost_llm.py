"""Bifrost LLM cost extractor.

Reads LLM request logs from the Bifrost gateway's PostgreSQL database,
maps virtual_key to project metadata, normalizes into NormalizedCostRecord,
and batch-inserts into the FinOps cost_records table.

Designed to run as a Cloud Run Job with incremental extraction via
extractor_health tracking.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

import psycopg
import yaml
from psycopg.rows import dict_row

from models import NormalizedCostRecord, Provider, ServiceCategory

logger = logging.getLogger("bifrost_llm_extractor")

EXTRACTOR_NAME = "bifrost_llm"

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


def _env(key: str, default: Optional[str] = None) -> str:
    """Read a required environment variable, raising if missing."""
    value = os.environ.get(key, default)
    if value is None:
        raise EnvironmentError(f"Required env var {key!r} is not set")
    return value


def load_key_mapping(path: str | Path) -> dict[str, dict[str, str]]:
    """Load the virtual_key → project mapping from YAML.

    Returns:
        dict mapping virtual_key strings to their metadata dicts.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Bifrost key mapping file not found: {path}")
    with path.open() as f:
        data = yaml.safe_load(f)
    mappings: dict[str, dict[str, str]] = data.get("mappings", {})
    if not mappings:
        raise ValueError(f"No mappings found in {path}")
    return mappings


# ---------------------------------------------------------------------------
# Incremental extraction state
# ---------------------------------------------------------------------------


def get_last_ingested_ts(conn: psycopg.Connection) -> Optional[datetime]:
    """Read last_ingested_ts from extractor_health for this extractor.

    We store the watermark in the error_message column as an ISO timestamp
    string, since the schema only has a fixed set of columns. A cleaner
    approach would add a dedicated column, but we work with what exists.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT error_message FROM extractor_health WHERE extractor_name = %s",
            (EXTRACTOR_NAME,),
        )
        row = cur.fetchone()
        if row and row.get("error_message"):
            try:
                return datetime.fromisoformat(row["error_message"])
            except (ValueError, TypeError):
                logger.warning("Could not parse stored watermark, starting fresh")
    return None


def mark_extractor_running(conn: psycopg.Connection) -> None:
    """Mark the extractor as running in the health table."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO extractor_health (extractor_name, last_run_start, status, updated_at)
            VALUES (%s, now(), 'running', now())
            ON CONFLICT (extractor_name)
            DO UPDATE SET last_run_start = now(), status = 'running', updated_at = now()
            """,
            (EXTRACTOR_NAME,),
        )
    conn.commit()


def mark_extractor_done(
    conn: psycopg.Connection,
    records_extracted: int,
    watermark: datetime,
) -> None:
    """Mark the extractor as succeeded and store the new watermark."""
    watermark_str = watermark.isoformat()
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE extractor_health
            SET last_run_end = now(),
                status = 'success',
                records_extracted = %s,
                error_message = %s,
                updated_at = now()
            WHERE extractor_name = %s
            """,
            (records_extracted, watermark_str, EXTRACTOR_NAME),
        )
    conn.commit()


def mark_extractor_failed(conn: psycopg.Connection, error_msg: str) -> None:
    """Mark the extractor as failed."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE extractor_health
            SET last_run_end = now(),
                status = 'failed',
                error_message = %s,
                updated_at = now()
            WHERE extractor_name = %s
            """,
            (error_msg[:2000], EXTRACTOR_NAME),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Bifrost log reading
# ---------------------------------------------------------------------------


def fetch_bifrost_logs(
    conn: psycopg.Connection,
    since: Optional[datetime] = None,
    batch_size: int = 1000,
) -> list[dict[str, Any]]:
    """Fetch LLM request logs from Bifrost's database.

    Args:
        conn: Connection to the Bifrost PostgreSQL database.
        since: If set, only fetch records with timestamp > since.
        batch_size: Maximum number of rows to return.

    Returns:
        List of dicts with keys: model, provider, input_tokens, output_tokens,
        cost, latency, virtual_key, timestamp.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        if since is not None:
            cur.execute(
                """
                SELECT
                    model,
                    provider,
                    input_tokens,
                    output_tokens,
                    cost,
                    latency,
                    virtual_key,
                    timestamp
                FROM log
                WHERE timestamp > %s
                ORDER BY timestamp ASC
                LIMIT %s
                """,
                (since, batch_size),
            )
        else:
            cur.execute(
                """
                SELECT
                    model,
                    provider,
                    input_tokens,
                    output_tokens,
                    cost,
                    latency,
                    virtual_key,
                    timestamp
                FROM log
                ORDER BY timestamp ASC
                LIMIT %s
                """,
                (batch_size,),
            )
        rows = cur.fetchall()
    logger.info("Fetched %d log records from Bifrost (since=%s)", len(rows), since)
    return rows


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def normalize_log(
    log: dict[str, Any],
    key_mapping: dict[str, dict[str, str]],
) -> Optional[NormalizedCostRecord]:
    """Convert a single Bifrost log row into a NormalizedCostRecord.

    Args:
        log: Dict from Bifrost's log table.
        key_mapping: virtual_key → project metadata mapping.

    Returns:
        NormalizedCostRecord, or None if the virtual_key is unmapped.
    """
    virtual_key = log.get("virtual_key", "")
    mapping = key_mapping.get(virtual_key)
    if mapping is None:
        logger.warning("Unmapped virtual_key=%r, skipping record", virtual_key)
        return None

    ts: datetime = log["timestamp"]
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    cost_value = Decimal(str(log.get("cost", 0)))
    input_tok = log.get("input_tokens")
    output_tok = log.get("output_tokens")
    total_tok = (input_tok or 0) + (output_tok or 0) if input_tok is not None and output_tok is not None else None
    latency = log.get("latency")

    model_name = log.get("model", "unknown")
    llm_provider = log.get("provider", "unknown")

    record = NormalizedCostRecord(
        provider=Provider.LLM,
        usage_start=ts,
        usage_end=ts,
        account_id="bifrost-gateway",
        account_name="Bifrost LLM Gateway",
        project_id=mapping["project_id"],
        project_name=mapping.get("project_name"),
        environment=mapping.get("environment"),
        team=mapping.get("team"),
        service_category=ServiceCategory.LLM,
        service_name=model_name,
        resource_id=None,
        cost_usd=cost_value,
        currency_original="USD",
        cost_original=cost_value,
        discount_usd=Decimal("0"),
        net_cost_usd=cost_value,
        usage_quantity=Decimal(str(total_tok)) if total_tok is not None else None,
        usage_unit="tokens",
        model_name=model_name,
        input_tokens=input_tok,
        output_tokens=output_tok,
        total_tokens=total_tok,
        latency_ms=float(latency) if latency is not None else None,
        trace_id=None,
        tags={"virtual_key": virtual_key, "llm_provider": llm_provider},
    )
    return record


# ---------------------------------------------------------------------------
# Batch insert
# ---------------------------------------------------------------------------

_INSERT_SQL = """
INSERT INTO cost_records (
    record_id, provider, usage_start, usage_end, ingestion_ts,
    account_id, account_name, project_id, project_name, environment, team,
    service_category, service_name, resource_id,
    cost_usd, currency_original, cost_original, discount_usd, net_cost_usd,
    usage_quantity, usage_unit,
    model_name, input_tokens, output_tokens, total_tokens, latency_ms, trace_id, tags
) VALUES (
    %(record_id)s, %(provider)s, %(usage_start)s, %(usage_end)s, %(ingestion_ts)s,
    %(account_id)s, %(account_name)s, %(project_id)s, %(project_name)s, %(environment)s, %(team)s,
    %(service_category)s, %(service_name)s, %(resource_id)s,
    %(cost_usd)s, %(currency_original)s, %(cost_original)s, %(discount_usd)s, %(net_cost_usd)s,
    %(usage_quantity)s, %(usage_unit)s,
    %(model_name)s, %(input_tokens)s, %(output_tokens)s, %(total_tokens)s, %(latency_ms)s, %(trace_id)s, %(tags)s
)
"""


def batch_insert(
    conn: psycopg.Connection,
    records: list[NormalizedCostRecord],
) -> int:
    """Insert NormalizedCostRecords into cost_records in one batch.

    Returns:
        Number of records inserted.
    """
    if not records:
        return 0

    # Convert to dicts suitable for psycopg execute_values-style batch insert
    payload = []
    for rec in records:
        d = rec.model_dump()
        # psycopg needs tz-aware datetimes; ensure they are
        for key in ("usage_start", "usage_end", "ingestion_ts"):
            if d[key] is not None and isinstance(d[key], datetime):
                if d[key].tzinfo is None:
                    d[key] = d[key].replace(tzinfo=timezone.utc)
        payload.append(d)

    with conn.cursor() as cur:
        cur.execute_batch(_INSERT_SQL, payload)
    conn.commit()
    logger.info("Inserted %d records into cost_records", len(records))
    return len(records)


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    """Cloud Run Job entrypoint for the Bifrost LLM extractor."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    bifrost_dsn = _env("BIFROST_PG_DSN")
    finops_dsn = _env("PG_DSN")
    mapping_path = os.environ.get("BIFROST_KEY_MAPPING_PATH", "config/bifrost_key_mapping.yaml")
    batch_size = int(os.environ.get("BATCH_SIZE", "1000"))

    key_mapping = load_key_mapping(mapping_path)
    logger.info("Loaded %d virtual_key mappings", len(key_mapping))

    # --- FinOps DB: mark running & get watermark --------------------------------
    finops_conn = psycopg.connect(finops_dsn, row_factory=dict_row, autocommit=True)
    mark_extractor_running(finops_conn)
    watermark = get_last_ingested_ts(finops_conn)
    logger.info("Watermark: %s", watermark or "(first run)")

    # --- Bifrost DB: fetch logs -------------------------------------------------
    bifrost_conn = psycopg.connect(bifrost_dsn, row_factory=dict_row)

    try:
        all_logs = fetch_bifrost_logs(bifrost_conn, since=watermark, batch_size=batch_size)

        if not all_logs:
            logger.info("No new Bifrost logs since last extraction")
            mark_extractor_done(finops_conn, records_extracted=0, watermark=watermark or datetime.now(timezone.utc))
            return

        # Normalize
        records: list[NormalizedCostRecord] = []
        skipped = 0
        for log_entry in all_logs:
            rec = normalize_log(log_entry, key_mapping)
            if rec is not None:
                records.append(rec)
            else:
                skipped += 1

        if skipped:
            logger.warning("Skipped %d records with unmapped virtual_keys", skipped)

        # Batch insert
        inserted = batch_insert(finops_conn, records)

        # Determine new watermark (latest timestamp from the logs we processed)
        latest_ts = max(r.usage_start for r in records)
        mark_extractor_done(finops_conn, records_extracted=inserted, watermark=latest_ts)
        logger.info("Extraction complete: %d records inserted, new watermark=%s", inserted, latest_ts)

    except Exception:
        logger.exception("Bifrost extraction failed")
        mark_extractor_failed(finops_conn, "See logs for details")
        sys.exit(1)

    finally:
        bifrost_conn.close()
        finops_conn.close()


if __name__ == "__main__":
    main()