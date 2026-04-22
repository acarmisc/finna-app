"""Extractor runner for API."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from psycopg.rows import dict_row

from .metrics import extractor_run_total

logger = logging.getLogger("api.runner")

# Global registry of running processes
_running_processes: dict[str, subprocess.Popen] = {}
_process_lock = threading.Lock()


def _get_pg_dsn() -> str:
    return os.getenv("PG_DSN", "")


def _get_extractor_type(provider: str) -> str:
    """Map provider to default extractor type."""
    mapping = {
        "azure": "azure_cost",
        "gcp": "gcp_billing",
    }
    return mapping.get(provider, provider)


def _build_env_from_config(config: dict[str, Any], provider: str, cred_type: str | None = None) -> dict[str, str]:
    """Build environment variables from cloud_config."""
    env = os.environ.copy()

    if provider == "azure":
        cred_type = cred_type or config.get("credential_type", "")

        # Use CLI auth if available (no client_secret needed)
        if cred_type == "cli" or not config.get("client_secret"):
            env["AZURE_AUTH_METHOD"] = "cli"
        else:
            env["AZURE_TENANT_ID"] = config.get("tenant_id", "")
            env["AZURE_CLIENT_ID"] = config.get("client_id", "")
            env["AZURE_CLIENT_SECRET"] = config.get("client_secret", "")

        env["AZURE_SUBSCRIPTION_ID"] = config.get("subscription_id", "")
        env["AZURE_SCOPE"] = config.get("scope", "resourcegroup")
        if config.get("resource_groups"):
            env["AZURE_RESOURCE_GROUP"] = config["resource_groups"][0]
            env["AZURE_RESOURCE_GROUPS"] = ",".join(config["resource_groups"])
            # space out per-RG API calls: 15s default, more RGs = more spacing
            n_rgs = len(config["resource_groups"])
            delay = max(15, n_rgs)
            env["RG_API_DELAY_SECS"] = str(delay)
            # shorter 429 retry waits for multi-RG runs to avoid hour-long hangs
            env["RATE_LIMIT_WAIT_1"] = "20"
            env["RATE_LIMIT_WAIT_2"] = "40"
            env["RATE_LIMIT_WAIT_3"] = "60"
    elif provider == "gcp":
        env["GCP_PROJECT"] = config.get("project_id", "")
        if config.get("bigquery_dataset"):
            env["BQ_DATASET"] = config["bigquery_dataset"]
        if config.get("bigquery_table"):
            env["BQ_TABLE"] = config["bigquery_table"]

    env["PG_DSN"] = _get_pg_dsn()

    return env


def _update_run_status(
    run_id: str,
    status: str,
    records_extracted: int = 0,
    error_message: Optional[str] = None,
    log_output: Optional[str] = None,
) -> None:
    """Update extractor_runs table."""
    from .db import get_connection

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE extractor_runs
                SET status = %s,
                    finished_at = %s,
                    records_extracted = %s,
                    error_message = %s,
                    log_output = %s
                WHERE id = %s
                """,
                (
                    status,
                    datetime.now(timezone.utc),
                    records_extracted,
                    error_message,
                    log_output,
                    run_id,
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def start_extractor(
    config_id: str,
    provider: str,
    extractor_type: Optional[str] = None,
    pg_dsn: Optional[str] = None,
) -> str:
    """Start an extractor as a subprocess.

    Returns the run_id.
    """
    from .db import get_connection, insert_and_return

    if pg_dsn is None:
        pg_dsn = _get_pg_dsn()
    if not pg_dsn:
        raise ValueError("PG_DSN not configured")

    extractor_type = _get_extractor_type(extractor_type or provider)

    # Get config + credential_type in one query
    conn = get_connection()
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT config, credential_type FROM cloud_config WHERE id = %s", (config_id,))
        row = cur.fetchone()
    if not row:
        raise ValueError(f"Config {config_id} not found")

    config = row["config"]
    config["credential_type"] = row["credential_type"]

    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    sql = """
        INSERT INTO extractor_runs (id, config_id, provider, extractor_type, status, started_at)
        VALUES (%s, %s, %s, %s, 'running', %s)
        RETURNING id
    """
    insert_and_return(sql, (run_id, config_id, provider, extractor_type, now))

    # Build command
    cmd = [sys.executable, "-m", f"extractors.{extractor_type}"]

    # Build environment (credential_type is now in config)
    env = _build_env_from_config(config, provider)

    # Start subprocess
    logger.info(f"Starting extractor {extractor_type} for config {config_id}")
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Increment extractor run counter on start
    extractor_run_total.labels(provider=provider, status="running").inc()

    # Register running process
    with _process_lock:
        _running_processes[run_id] = proc

    # Start background thread to monitor
    def monitor():
        output_lines = []
        try:
            while True:
                line = proc.stdout.readline()
                if line:
                    output_lines.append(line)
                elif proc.poll() is not None:
                    break

            output = "".join(output_lines)

            # Determine status
            records = 0
            if proc.returncode == 0:
                status = "success"
                error = None
                # Extract total record count — prefer "total records inserted" line
                for line in reversed(output_lines):
                    m = re.search(r"(\d+)\s+total\s+records\s+inserted", line)
                    if not m:
                        m = re.search(r"Inserted\s+(\d+)\s+of\s+\d+\s+records", line)
                    if not m:
                        m = re.search(r"completed:\s+(\d+)\s+records", line)
                    if m:
                        records = int(m.group(1))
                        break
            else:
                status = "failed"
                error = f"Exit code: {proc.returncode}"

            try:
                extractor_run_total.labels(provider=provider, status=status).inc()
            except Exception:
                logger.warning("Failed to increment extractor_run_total metric")

        except Exception as exc:
            output = "".join(output_lines)
            status = "failed"
            error = f"Monitor thread error: {exc}"
            records = 0

        _update_run_status(run_id, status, records, error, output)

        with _process_lock:
            _running_processes.pop(run_id, None)

        logger.info(f"Extractor {run_id} finished with status: {status}")

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()

    return run_id


def get_run_status(run_id: str) -> Optional[dict[str, Any]]:
    """Get status of a run."""
    from .db import query_one

    sql = """
        SELECT id, config_id, provider, extractor_type, status,
               started_at, finished_at, records_extracted, error_message, log_output
        FROM extractor_runs
        WHERE id = %s
    """
    return query_one(sql, (run_id,))


def list_runs(limit: int = 50, provider: Optional[str] = None) -> list[dict[str, Any]]:
    """List recent runs."""
    from .db import query_all

    if provider:
        sql = """
            SELECT id, config_id, provider, extractor_type, status,
                   started_at, finished_at, records_extracted
            FROM extractor_runs
            WHERE provider = %s
            ORDER BY started_at DESC
            LIMIT %s
        """
        return query_all(sql, (provider, limit))
    else:
        sql = """
            SELECT id, config_id, provider, extractor_type, status,
                   started_at, finished_at, records_extracted
            FROM extractor_runs
            ORDER BY started_at DESC
            LIMIT %s
        """
        return query_all(sql, (limit,))


def cancel_run(run_id: str) -> bool:
    """Cancel a running extractor."""
    with _process_lock:
        proc = _running_processes.get(run_id)
        if proc is None:
            return False

        proc.terminate()
        # Give it 10 seconds to terminate gracefully
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

        _update_run_status(run_id, "failed", 0, "Cancelled by user")
        _running_processes.pop(run_id, None)
        return True
