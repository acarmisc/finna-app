"""Extractor runner for API."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from typing import Any, Optional

from psycopg.rows import dict_row

from api.metrics import extractor_run_total

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
            env["AZURE_RESOURCE_GROUPS"] = ",".join(config["resource_groups"])
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
    from api.db import get_connection

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
    from api.db import get_connection, insert_and_return

    if pg_dsn is None:
        pg_dsn = _get_pg_dsn()
    if not pg_dsn:
        raise ValueError("PG_DSN not configured")

    if extractor_type is None:
        extractor_type = _get_extractor_type(provider)

    # Get config from DB
    conn = get_connection()
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT config FROM cloud_config WHERE id = %s", (config_id,))
        row = cur.fetchone()
    if not row:
        raise ValueError(f"Config {config_id} not found")

    config = row["config"]

    # Also get credential_type from cloud_config table
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT credential_type FROM cloud_config WHERE id = %s", (config_id,))
        config_row = cur.fetchone()
    if config_row:
        cred_type = config_row["credential_type"]
        config["credential_type"] = cred_type

    # Create run record
    import uuid

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
        while True:
            line = proc.stdout.readline()
            if line:
                output_lines.append(line)
            elif proc.poll() is not None:
                break

        output = "".join(output_lines)

        # Determine status
        if proc.returncode == 0:
            status = "success"
            error = None
            # Try to extract record count from output
            records = 0
            for line in output_lines:
                if "Inserted" in line and "records" in line:
                    try:
                        import re

                        match = re.search(r"(\d+)\s+records?", line)
                        if match:
                            records = int(match.group(1))
                    except Exception:
                        pass
        else:
            status = "failed"
            error = f"Exit code: {proc.returncode}"

        # Increment extractor run counter on completion
        extractor_run_total.labels(provider=provider, status=status).inc()

        _update_run_status(run_id, status, records, error, output)

        with _process_lock:
            _running_processes.pop(run_id, None)

        logger.info(f"Extractor {run_id} finished with status: {status}")

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()

    return run_id


def get_run_status(run_id: str) -> Optional[dict[str, Any]]:
    """Get status of a run."""
    from api.db import query_one

    sql = """
        SELECT id, config_id, provider, extractor_type, status,
               started_at, finished_at, records_extracted, error_message, log_output
        FROM extractor_runs
        WHERE id = %s
    """
    return query_one(sql, (run_id,))


def list_runs(limit: int = 50, provider: Optional[str] = None) -> list[dict[str, Any]]:
    """List recent runs."""
    from api.db import query_all

    if provider:
        sql = """
            SELECT id, config_id, provider, extractor_type, status,
                   started_at, finished_at, records_extracted
            FROM extractor_runs
            WHERE provider = %s
            ORDER BY started_at DESC
            LIMIT %s
        """
        return query_all(sql, (provider, str(limit)))
    else:
        sql = """
            SELECT id, config_id, provider, extractor_type, status,
                   started_at, finished_at, records_extracted
            FROM extractor_runs
            ORDER BY started_at DESC
            LIMIT %s
        """
        return query_all(sql, (str(limit),))


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
